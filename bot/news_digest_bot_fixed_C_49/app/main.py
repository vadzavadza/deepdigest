from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.internal import router as internal_router
from app.api.routes.telegram import router as telegram_router
from app.bot.application import get_bot_application
from app.infrastructure.db.session import init_db
from app.shared.logging import configure_logging
from app.shared.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings=settings)

    app = FastAPI(
        title="News Digest Bot",
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.bot_application = get_bot_application(settings=settings)

    app.include_router(internal_router, prefix="/internal", tags=["internal"])
    app.include_router(telegram_router, prefix="/telegram", tags=["telegram"])

    return app
