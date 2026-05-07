import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.db.base import Base
from app.infrastructure.db import models as _models  # noqa: F401
from app.shared.settings import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionFactory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def wait_for_database(max_attempts: int = 20, delay_seconds: float = 1.5) -> None:
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: None)
            return
        except Exception as exc:  # pragma: no cover - startup retry path
            last_error = exc
            await asyncio.sleep(delay_seconds)
    if last_error is not None:
        raise last_error


async def init_db() -> None:
    await wait_for_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
