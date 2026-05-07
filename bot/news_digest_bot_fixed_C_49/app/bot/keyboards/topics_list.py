from collections.abc import Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.db.models import Topic
from app.infrastructure.telegram.callbacks import topic_delete, topic_run, topic_view


def build_topics_list_keyboard(topics: Sequence[Topic]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for topic in topics:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📄 {topic.query_text}",
                    callback_data=topic_view(topic.id),
                ),
                InlineKeyboardButton(
                    text="▶️ Запустить сейчас",
                    callback_data=topic_run(topic.id),
                ),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=topic_delete(topic.id),
                )
            ]
        )
    return InlineKeyboardMarkup(rows)
