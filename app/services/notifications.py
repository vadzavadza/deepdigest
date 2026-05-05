import httpx
from app.core.config import settings

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Send message to a Telegram user. Returns True on success."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })
    return r.status_code == 200


async def notify_new_user(chat_id: str) -> None:
    await send_telegram_message(chat_id, (
        "🎉 <b>Welcome to DeepDigest!</b>\n\n"
        "Your account is confirmed. You'll receive your first digest today.\n\n"
        "Use /help to see available commands."
    ))


async def notify_digest_ready(chat_id: str, summary: str) -> None:
    await send_telegram_message(chat_id, (
        f"📰 <b>Your digest is ready</b>\n\n{summary}"
    ))
