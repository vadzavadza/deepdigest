import asyncio

from app.infrastructure.db.session import init_db
from app.infrastructure.scheduler.service import build_scheduler_runtime
from app.shared.logging import configure_logging
from app.shared.settings import get_settings


async def main() -> None:
    settings = get_settings()
    configure_logging(settings=settings)
    await init_db()
    runtime = await build_scheduler_runtime()
    runtime.start()

    stop_event = asyncio.Event()
    await stop_event.wait()


if __name__ == "__main__":
    asyncio.run(main())
