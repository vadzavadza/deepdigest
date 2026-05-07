from telegram import Update
from telegram.ext import ContextTypes

from app.infrastructure.telegram.service_messages import HELP_TEXT


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    if query.message is not None:
        await query.message.reply_text(text=HELP_TEXT)


async def placeholder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    if query.message is not None:
        await query.message.reply_text(
            text=(
                "Этот раздел я уже подключил в меню, но сам сценарий ещё дописываю. "
                "Сейчас рабочие команды: /start, /help и полный flow кнопки «Добавить тему»."
            )
        )
