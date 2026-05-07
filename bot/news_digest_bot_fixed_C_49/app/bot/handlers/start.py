from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.main_menu import build_main_menu
from app.infrastructure.telegram.service_messages import HELP_TEXT, START_TEXT


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        text=START_TEXT,
        reply_markup=build_main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(text=HELP_TEXT)
