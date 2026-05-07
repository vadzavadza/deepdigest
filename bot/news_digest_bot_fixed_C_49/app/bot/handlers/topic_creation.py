from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.main_menu import build_main_menu
from app.bot.keyboards.topic_creation import (
    build_channel_keyboard,
    build_language_keyboard,
    build_mode_keyboard,
)
from app.domain.enums import DeliveryMode, OutputLanguage
from app.infrastructure.db.models import Channel, Topic, User
from app.infrastructure.db.session import SessionFactory
from app.shared.settings import get_settings

TOPIC_CREATION_STATE_KEY = "topic_creation_state"
TOPIC_CREATION_DRAFT_KEY = "topic_creation_draft"

TOPIC_CREATION_AWAITING_QUERY = "awaiting_query_text"
TOPIC_CREATION_AWAITING_TIME = "awaiting_delivery_time"


@dataclass(slots=True)
class TopicDraft:
    query_text: str | None = None
    output_language: str | None = None
    mode: str | None = None
    delivery_time: str | None = None

    def as_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.query_text is not None:
            payload["query_text"] = self.query_text
        if self.output_language is not None:
            payload["output_language"] = self.output_language
        if self.mode is not None:
            payload["mode"] = self.mode
        if self.delivery_time is not None:
            payload["delivery_time"] = self.delivery_time
        return payload

    @classmethod
    def from_mapping(cls, value: dict[str, str] | None) -> "TopicDraft":
        if value is None:
            return cls()
        return cls(
            query_text=value.get("query_text"),
            output_language=value.get("output_language"),
            mode=value.get("mode"),
            delivery_time=value.get("delivery_time"),
        )


def _get_draft(context: ContextTypes.DEFAULT_TYPE) -> TopicDraft:
    return TopicDraft.from_mapping(context.user_data.get(TOPIC_CREATION_DRAFT_KEY))


def _save_draft(context: ContextTypes.DEFAULT_TYPE, draft: TopicDraft) -> None:
    context.user_data[TOPIC_CREATION_DRAFT_KEY] = draft.as_dict()


def _clear_creation_state_only(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(TOPIC_CREATION_STATE_KEY, None)


def _clear_creation_all(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(TOPIC_CREATION_STATE_KEY, None)
    context.user_data.pop(TOPIC_CREATION_DRAFT_KEY, None)


async def start_topic_creation_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    context.user_data[TOPIC_CREATION_STATE_KEY] = TOPIC_CREATION_AWAITING_QUERY
    _save_draft(context, TopicDraft())

    if query.message is not None:
        await query.message.reply_text(
            text=(
                "Шаг 1 из 4: пришли тему одним сообщением.\n\n"
                "Пример: BMW, bitcoin, OpenAI, Real Madrid, Iran.\n"
                "Длина темы: от 1 до 200 символов."
            )
        )


async def topic_creation_language_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    payload = query.data or ""
    selected_language = payload.rsplit(":", 1)[-1]
    if selected_language not in {OutputLanguage.EN.value, OutputLanguage.DE.value}:
        return

    draft = _get_draft(context)
    draft.output_language = selected_language
    _save_draft(context, draft)

    if query.message is not None:
        readable = "English" if selected_language == OutputLanguage.EN.value else "Deutsch"
        await query.message.reply_text(
            text=(
                f"Шаг 2 из 4 сохранён. Язык: {readable}.\n\n"
                "Теперь выбери режим:"
            ),
            reply_markup=build_mode_keyboard(),
        )


async def topic_creation_mode_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    payload = query.data or ""
    selected_mode = payload.rsplit(":", 1)[-1]
    if selected_mode not in {DeliveryMode.LATEST.value, DeliveryMode.DAILY_DIGEST.value}:
        return

    draft = _get_draft(context)
    draft.mode = selected_mode
    _save_draft(context, draft)
    context.user_data[TOPIC_CREATION_STATE_KEY] = TOPIC_CREATION_AWAITING_TIME

    if query.message is not None:
        readable = "latest" if selected_mode == DeliveryMode.LATEST.value else "daily_digest"
        await query.message.reply_text(
            text=(
                f"Шаг 3 из 4 сохранён. Режим: {readable}.\n\n"
                "Теперь пришли время в формате HH:MM.\n"
                "Пример: 08:00 или 19:30"
            )
        )


async def topic_creation_channel_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    payload = query.data or ""

    draft = _get_draft(context)
    if not all([draft.query_text, draft.output_language, draft.mode, draft.delivery_time]):
        if query.message is not None:
            await query.message.reply_text(
                text="Черновик не полный. Давай начнём заново через кнопку «Добавить тему»."
            )
        _clear_creation_all(context)
        return

    if payload == "topic:create:channel:personal":
        topic, destination_title = await _persist_topic_from_draft(
            update=update,
            draft=draft,
            use_current_chat=True,
            selected_channel_id=None,
        )
    elif payload.startswith("topic:create:channel:saved:"):
        try:
            channel_id = int(payload.rsplit(":", 1)[-1])
        except ValueError:
            return
        topic, destination_title = await _persist_topic_from_draft(
            update=update,
            draft=draft,
            use_current_chat=False,
            selected_channel_id=channel_id,
        )
    else:
        return

    _clear_creation_all(context)

    if query.message is not None:
        await query.message.reply_text(
            text=(
                "Тема сохранена.\n\n"
                f"Тема: {topic.query_text}\n"
                f"Язык: {topic.output_language}\n"
                f"Режим: {topic.mode}\n"
                f"Время: {topic.delivery_time.strftime('%H:%M')}\n"
                f"Timezone: {get_settings().default_timezone}\n"
                f"Куда отправлять: {destination_title}"
            ),
            reply_markup=build_main_menu(),
        )


async def topic_creation_text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.effective_message is None:
        return

    state = context.user_data.get(TOPIC_CREATION_STATE_KEY)
    if state == TOPIC_CREATION_AWAITING_QUERY:
        await _handle_query_text(update, context)
        return
    if state == TOPIC_CREATION_AWAITING_TIME:
        await _handle_delivery_time(update, context)
        return


async def _handle_query_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return

    raw_text = (update.effective_message.text or "").strip()
    if not raw_text:
        await update.effective_message.reply_text(
            text="Тема не должна быть пустой. Пришли тему одним сообщением."
        )
        return

    if len(raw_text) > 200:
        await update.effective_message.reply_text(
            text="Тема слишком длинная. Нужна строка до 200 символов. Попробуй ещё раз."
        )
        return

    draft = _get_draft(context)
    draft.query_text = raw_text
    _save_draft(context, draft)
    _clear_creation_state_only(context)

    await update.effective_message.reply_text(
        text=(
            f"Шаг 1 из 4 сохранён. Тема: {raw_text}.\n\n"
            "Шаг 2 из 4: выбери язык выдачи."
        ),
        reply_markup=build_language_keyboard(),
    )


async def _handle_delivery_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return

    raw_text = (update.effective_message.text or "").strip()
    parsed_time = _parse_time(raw_text)
    if parsed_time is None:
        await update.effective_message.reply_text(
            text="Неверный формат времени. Нужен формат HH:MM, например 08:00 или 19:30."
        )
        return

    draft = _get_draft(context)
    draft.delivery_time = parsed_time.strftime("%H:%M")
    _save_draft(context, draft)
    _clear_creation_state_only(context)

    saved_channels = await _load_saved_channels_for_user(update=update)

    await update.effective_message.reply_text(
        text=(
            f"Шаг 4 из 4 сохранён. Время: {draft.delivery_time}.\n\n"
            "Теперь выбери, куда отправлять новости:\n"
            "• в личный чат с ботом\n"
            "• или в один из сохранённых каналов публикации"
        ),
        reply_markup=build_channel_keyboard(saved_channels=saved_channels),
    )


def _parse_time(raw_text: str) -> time | None:
    try:
        return datetime.strptime(raw_text, "%H:%M").time()
    except ValueError:
        return None


async def _persist_topic_from_draft(
    *,
    update: Update,
    draft: TopicDraft,
    use_current_chat: bool,
    selected_channel_id: int | None,
) -> tuple[Topic, str]:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        raise RuntimeError("Missing Telegram user/chat context for topic creation")

    settings = get_settings()
    chat_title = effective_chat.title or effective_user.full_name or "Direct chat"
    delivery_time = _parse_time(draft.delivery_time or "")
    if delivery_time is None:
        raise RuntimeError("Invalid delivery time in topic draft")

    async with SessionFactory() as session:
        user = await _get_or_create_user(session, telegram_user_id=effective_user.id)
        if use_current_chat:
            channel = await _get_or_create_channel(
                session,
                user_id=user.id,
                telegram_chat_id=effective_chat.id,
                title=chat_title,
            )
            destination_title = f"личный чат ({chat_title})"
        else:
            channel = await _get_existing_channel_for_user(
                session,
                user_id=user.id,
                channel_id=selected_channel_id,
            )
            if channel is None:
                raise RuntimeError("Selected publication channel not found")
            destination_title = channel.title

        topic = Topic(
            user_id=user.id,
            channel_id=channel.id,
            query_text=draft.query_text or "",
            output_language=draft.output_language or settings.default_output_language,
            delivery_time=delivery_time,
            timezone=settings.default_timezone,
            mode=draft.mode or DeliveryMode.DAILY_DIGEST.value,
            is_active=True,
        )
        session.add(topic)
        await session.commit()
        await session.refresh(topic)
        return topic, destination_title


async def _load_saved_channels_for_user(update: Update) -> list[Channel]:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None:
        return []

    async with SessionFactory() as session:
        result = await session.execute(select(User).where(User.telegram_user_id == effective_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            return []

        result = await session.execute(
            select(Channel).where(
                Channel.user_id == user.id,
                Channel.is_active.is_(True),
            )
        )
        channels = list(result.scalars().all())
        if effective_chat is None:
            return channels
        return [channel for channel in channels if channel.telegram_chat_id != effective_chat.id]


async def _get_or_create_user(session: AsyncSession, *, telegram_user_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(telegram_user_id=telegram_user_id, locale=None)
    session.add(user)
    await session.flush()
    return user


async def _get_or_create_channel(
    session: AsyncSession,
    *,
    user_id: int,
    telegram_chat_id: int,
    title: str,
) -> Channel:
    result = await session.execute(select(Channel).where(Channel.telegram_chat_id == telegram_chat_id))
    channel = result.scalar_one_or_none()
    if channel is not None:
        return channel

    channel = Channel(
        user_id=user_id,
        telegram_chat_id=telegram_chat_id,
        title=title,
        is_active=True,
    )
    session.add(channel)
    await session.flush()
    return channel


async def _get_existing_channel_for_user(
    session: AsyncSession,
    *,
    user_id: int,
    channel_id: int | None,
) -> Channel | None:
    if channel_id is None:
        return None
    result = await session.execute(
        select(Channel).where(
            Channel.id == channel_id,
            Channel.user_id == user_id,
            Channel.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()
