from fastapi import APIRouter, Header, HTTPException, Request
from telegram import Update

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    settings = request.app.state.settings
    if settings.webhook_secret_token and (
        x_telegram_bot_api_secret_token != settings.webhook_secret_token
    ):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    payload = await request.json()
    bot_application = request.app.state.bot_application
    update = Update.de_json(payload, bot_application.bot)
    await bot_application.initialize()
    await bot_application.process_update(update)
    return {"ok": True}
