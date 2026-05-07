from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.telegram.callbacks import (
    channels_list,
    help_open,
    settings_open,
    topic_create,
    topics_list,
)


def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="Добавить тему", callback_data=topic_create())],
            [InlineKeyboardButton(text="Мои темы", callback_data=topics_list())],
            [InlineKeyboardButton(text="Каналы", callback_data=channels_list())],
            [InlineKeyboardButton(text="Настройки", callback_data=settings_open())],
            [InlineKeyboardButton(text="Помощь", callback_data=help_open())],
        ]
    )
