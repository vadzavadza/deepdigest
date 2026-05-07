from html import escape

from telegram import Bot

from app.schemas.publishing import PublishPayload


class TelegramPublisher:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    def render_message(self, payload: PublishPayload) -> str:
        lines = [
            f"<b>{escape(payload.query_text)} - {escape(payload.mode.value)} digest</b>",
            "",
        ]
        for index, item in enumerate(payload.items, start=1):
            lines.extend(
                [
                    f"<b>{index}. {escape(item.title)}</b>",
                    escape(item.summary),
                    f"Source: {escape(item.source_name)}",
                    f"Original language: {escape(item.source_language)}",
                    f'<a href="{item.link}">Статья</a>',
                    "",
                ]
            )
        return "\n".join(lines).strip()

    async def publish(self, *, channel_chat_id: int, payload: PublishPayload) -> int:
        message = self.render_message(payload=payload)
        sent = await self._bot.send_message(
            chat_id=channel_chat_id,
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
        return sent.message_id
