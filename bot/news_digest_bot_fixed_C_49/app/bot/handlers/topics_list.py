from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import Update
from telegram.ext import ContextTypes

from app.application.services.topic_processing import TopicProcessingOutcome, TopicProcessingService
from app.bot.keyboards.main_menu import build_main_menu
from app.bot.keyboards.topic_details import build_topic_detail_keyboard
from app.bot.keyboards.topics_list import build_topics_list_keyboard
from app.infrastructure.db.models import Topic, User
from app.infrastructure.db.session import SessionFactory
from app.infrastructure.llm.openrouter import OpenRouterProvider
from app.infrastructure.sources.factory import build_source_registry
from app.infrastructure.telegram.publisher import TelegramPublisher


async def topics_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    effective_user = update.effective_user
    if effective_user is None or query.message is None:
        return

    topics = await _load_topics_for_user(telegram_user_id=effective_user.id)
    if not topics:
        await query.message.reply_text(
            text=(
                "Список тем пока пуст.\n\n"
                "Нажми «Добавить тему», чтобы создать первую тему мониторинга."
            ),
            reply_markup=build_main_menu(),
        )
        return

    lines = ["Твои сохранённые темы:", ""]
    for index, topic in enumerate(topics, start=1):
        lines.append(
            f"{index}. {topic.query_text} — {topic.output_language} — {topic.mode} — {topic.delivery_time.strftime('%H:%M')}"
        )

    await query.message.reply_text(
        text="\n".join(lines),
        reply_markup=build_topics_list_keyboard(topics),
    )


async def topic_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    effective_user = update.effective_user
    if effective_user is None or query.message is None:
        return

    payload = query.data or ""
    try:
        topic_id = int(payload.split(":")[1])
    except (IndexError, ValueError):
        return

    topic = await _load_topic_for_user(telegram_user_id=effective_user.id, topic_id=topic_id)
    if topic is None:
        await query.message.reply_text(text="Не нашёл эту тему. Возможно, она уже удалена.")
        return

    await query.message.reply_text(
        text=(
            "Карточка темы:\n\n"
            f"ID: {topic.id}\n"
            f"Тема: {topic.query_text}\n"
            f"Язык: {topic.output_language}\n"
            f"Режим: {topic.mode}\n"
            f"Время: {topic.delivery_time.strftime('%H:%M')}\n"
            f"Timezone: {topic.timezone}\n"
            f"Активна: {'да' if topic.is_active else 'нет'}"
        ),
        reply_markup=build_topic_detail_keyboard(topic.id),
    )


async def topic_run_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer("Запускаю тему…")
    effective_user = update.effective_user
    if effective_user is None or query.message is None:
        return

    payload = query.data or ""
    try:
        topic_id = int(payload.split(":")[1])
    except (IndexError, ValueError):
        return

    topic = await _load_topic_for_user(telegram_user_id=effective_user.id, topic_id=topic_id)
    if topic is None:
        await query.message.reply_text(text="Не нашёл эту тему. Возможно, она уже удалена.")
        return

    await query.message.reply_text(
        text=(
            f"Запускаю поиск по теме: {topic.query_text}.\n"
            "Это может занять 10–40 секунд."
        )
    )

    try:
        async with SessionFactory() as session:
            service = TopicProcessingService(
                session=session,
                source_registry=build_source_registry(),
                llm_provider=OpenRouterProvider(),
                publisher=TelegramPublisher(context.bot),
            )
            result = await service.process_topic(topic_id=topic.id, force=False)
    except Exception as exc:
        await query.message.reply_text(
            text=(
                "Во время ручного запуска произошла ошибка.\n"
                "Проверь OpenRouter API key и попробуй ещё раз.\n\n"
                f"Техническая деталь: {type(exc).__name__}"
            ),
            reply_markup=build_main_menu(),
        )
        return

    await _send_run_result_message(query.message, topic.query_text, result)


async def _send_run_result_message(message, topic_query: str, result: TopicProcessingOutcome) -> None:
    source_lines = []
    for stat in result.source_stats:
        status = "ошибка" if stat.failed else f"получено: {stat.fetched_count}"
        line = f"• {stat.source_name}: {status}"
        if stat.error_message and stat.failed:
            line += f" ({stat.error_message[:120]})"
        source_lines.append(line)

    diagnostics = "\n".join(source_lines)
    extra_lines = []
    if result.skipped_already_sent:
        extra_lines.append(f"• уже отправлялось раньше: {result.skipped_already_sent}")
    if result.skipped_immediate_repeat:
        extra_lines.append(f"• скрыто повторным запуском: {result.skipped_immediate_repeat}")
    if result.skipped_low_quality:
        extra_lines.append(f"• не прошло quality-gate: {result.skipped_low_quality}")
    if extra_lines:
        diagnostics = (diagnostics + "\n" if diagnostics else "") + "Диагностика:\n" + "\n".join(extra_lines)
    if diagnostics:
        diagnostics = f"\n\nИсточники/диагностика:\n{diagnostics}"

    if result.sent_count > 0:
        await message.reply_text(
            text=(
                f"Готово. Тема «{topic_query}» обработана.\n"
                f"Найдено материалов: {result.found_articles}\n"
                f"Уникальных сюжетов: {result.unique_stories}\n"
                f"Отправлено в чат: {result.sent_count}"
                f"{diagnostics}"
            ),
            reply_markup=build_main_menu(),
        )
        return

    await message.reply_text(
        text=(
            f"Обработка темы «{topic_query}» завершена, но новых новостей для отправки нет.\n\n"
            f"Найдено материалов: {result.found_articles}\n"
            f"Уникальных сюжетов: {result.unique_stories}\n"
            "Попробуй позже или используй другую тему."
            f"{diagnostics}"
        ),
        reply_markup=build_main_menu(),
    )


async def topic_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    effective_user = update.effective_user
    if effective_user is None or query.message is None:
        return

    payload = query.data or ""
    try:
        topic_id = int(payload.split(":")[1])
    except (IndexError, ValueError):
        return

    deleted_query = await _deactivate_topic_for_user(
        telegram_user_id=effective_user.id,
        topic_id=topic_id,
    )
    if deleted_query is None:
        await query.message.reply_text(text="Не смог удалить тему. Возможно, она уже была удалена.")
        return

    await query.message.reply_text(
        text=f"Тема удалена: {deleted_query}",
        reply_markup=build_main_menu(),
    )


async def _load_topics_for_user(*, telegram_user_id: int) -> list[Topic]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Topic)
            .join(User, User.id == Topic.user_id)
            .where(User.telegram_user_id == telegram_user_id, Topic.is_active.is_(True))
            .order_by(Topic.created_at.desc())
        )
        return list(result.scalars().all())


async def _load_topic_for_user(*, telegram_user_id: int, topic_id: int) -> Topic | None:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Topic)
            .options(selectinload(Topic.channel))
            .join(User, User.id == Topic.user_id)
            .where(
                User.telegram_user_id == telegram_user_id,
                Topic.id == topic_id,
                Topic.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()


async def _deactivate_topic_for_user(*, telegram_user_id: int, topic_id: int) -> str | None:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Topic)
            .join(User, User.id == Topic.user_id)
            .where(
                User.telegram_user_id == telegram_user_id,
                Topic.id == topic_id,
                Topic.is_active.is_(True),
            )
        )
        topic = result.scalar_one_or_none()
        if topic is None:
            return None

        topic.is_active = False
        await session.commit()
        return topic.query_text
