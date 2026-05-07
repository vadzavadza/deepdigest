from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.telegram.callbacks import channel_register_this_chat


def build_channels_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="➕ Сохранить этот чат", callback_data=channel_register_this_chat())]]
    )
