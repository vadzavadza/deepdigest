from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.bot.handlers.callbacks import help_callback, placeholder_callback
from app.bot.handlers.channels import channels_list_callback, register_current_chat_channel_callback
from app.bot.handlers.start import help_command, start_command
from app.bot.handlers.topic_creation import (
    start_topic_creation_callback,
    topic_creation_channel_callback,
    topic_creation_language_callback,
    topic_creation_mode_callback,
    topic_creation_text_message,
)
from app.bot.handlers.topics_list import (
    topic_delete_callback,
    topic_run_callback,
    topic_view_callback,
    topics_list_callback,
)
from app.shared.settings import Settings


def get_bot_application(*, settings: Settings) -> Application:
    application = Application.builder().token(settings.bot_token).updater(None).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help:open$"))
    application.add_handler(CallbackQueryHandler(start_topic_creation_callback, pattern=r"^topic:create$"))
    application.add_handler(
        CallbackQueryHandler(
            topic_creation_language_callback,
            pattern=r"^topic:create:lang:(en|de)$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            topic_creation_mode_callback,
            pattern=r"^topic:create:mode:(latest|daily_digest)$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            topic_creation_channel_callback,
            pattern=r"^topic:create:channel:(personal|saved:\d+)$",
        )
    )
    application.add_handler(CallbackQueryHandler(topics_list_callback, pattern=r"^topics:list$"))
    application.add_handler(CallbackQueryHandler(channels_list_callback, pattern=r"^channels:list$"))
    application.add_handler(CallbackQueryHandler(register_current_chat_channel_callback, pattern=r"^channels:register:this_chat$"))
    application.add_handler(CallbackQueryHandler(topic_view_callback, pattern=r"^topic:\d+:view$"))
    application.add_handler(CallbackQueryHandler(topic_run_callback, pattern=r"^topic:\d+:run$"))
    application.add_handler(CallbackQueryHandler(topic_delete_callback, pattern=r"^topic:\d+:delete$"))
    application.add_handler(
        CallbackQueryHandler(
            placeholder_callback,
            pattern=r"^settings:open$",
        )
    )
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, topic_creation_text_message))
    return application
