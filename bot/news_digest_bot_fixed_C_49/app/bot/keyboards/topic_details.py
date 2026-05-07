from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.telegram.callbacks import topic_delete, topic_run


def build_topic_detail_keyboard(topic_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="▶️ Запустить сейчас", callback_data=topic_run(topic_id))],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=topic_delete(topic_id))],
        ]
    )
