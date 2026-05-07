from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.db.models import Channel


def build_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="English", callback_data="topic:create:lang:en"),
                InlineKeyboardButton(text="Deutsch", callback_data="topic:create:lang:de"),
            ]
        ]
    )


def build_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="Latest", callback_data="topic:create:mode:latest")],
            [
                InlineKeyboardButton(
                    text="Daily digest",
                    callback_data="topic:create:mode:daily_digest",
                )
            ],
        ]
    )


def build_channel_keyboard(*, saved_channels: list[Channel]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="Личный чат",
                callback_data="topic:create:channel:personal",
            )
        ]
    ]

    for channel in saved_channels:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Канал: {channel.title}",
                    callback_data=f"topic:create:channel:saved:{channel.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(rows)
