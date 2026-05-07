from __future__ import annotations

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.channels import build_channels_keyboard
from app.bot.keyboards.main_menu import build_main_menu
from app.infrastructure.db.models import Channel, User
from app.infrastructure.db.session import SessionFactory


async def channels_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    effective_user = update.effective_user
    if effective_user is None or query.message is None:
        return

    channels = await _load_channels_for_user(telegram_user_id=effective_user.id)
    if not channels:
        await query.message.reply_text(
            text=(
                "Каналы публикации пока пусты.\n\n"
                "Здесь будут Telegram-каналы или чаты, куда бот сможет отправлять готовые новости.\n"
                "Личный чат и сохранённые каналы — это варианты доставки. Для MVP можно сохранить текущий чат как место публикации."
            ),
            reply_markup=build_channels_keyboard(),
        )
        return

    lines = ["Твои каналы публикации:", ""]
    for index, channel in enumerate(channels, start=1):
        lines.append(f"{index}. {channel.title} — chat_id {channel.telegram_chat_id}")

    lines.append(
        "\nПри создании темы можно выбрать личный чат или один из сохранённых каналов публикации."
    )

    await query.message.reply_text(
        text="\n".join(lines),
        reply_markup=build_channels_keyboard(),
    )


async def register_current_chat_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None or query.message is None:
        return

    saved_title, already_existed = await _save_current_chat_channel(
        telegram_user_id=effective_user.id,
        telegram_chat_id=effective_chat.id,
        title=effective_chat.title or effective_user.full_name or "Direct chat",
    )

    prefix = "Этот чат уже был сохранён" if already_existed else "Сохранил канал публикации"
    await query.message.reply_text(
        text=(
            f"{prefix}: {saved_title}.\n\n"
            "Теперь этот чат числится как канал публикации для MVP."
        ),
        reply_markup=build_main_menu(),
    )


async def _load_channels_for_user(*, telegram_user_id: int) -> list[Channel]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Channel)
            .join(User, User.id == Channel.user_id)
            .where(User.telegram_user_id == telegram_user_id, Channel.is_active.is_(True))
            .order_by(Channel.created_at.desc())
        )
        return list(result.scalars().all())


async def _save_current_chat_channel(*, telegram_user_id: int, telegram_chat_id: int, title: str) -> tuple[str, bool]:
    async with SessionFactory() as session:
        user = await _get_or_create_user(session, telegram_user_id=telegram_user_id)
        result = await session.execute(select(Channel).where(Channel.telegram_chat_id == telegram_chat_id))
        channel = result.scalar_one_or_none()
        if channel is not None:
            if channel.title != title:
                channel.title = title
                await session.commit()
            return channel.title, True

        channel = Channel(
            user_id=user.id,
            telegram_chat_id=telegram_chat_id,
            title=title,
            is_active=True,
        )
        session.add(channel)
        await session.commit()
        return channel.title, False


async def _get_or_create_user(session, *, telegram_user_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(telegram_user_id=telegram_user_id, locale=None)
    session.add(user)
    await session.flush()
    return user
