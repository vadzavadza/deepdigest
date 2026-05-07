from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from app.application.services.topic_processing import TopicProcessingService
from app.infrastructure.db.session import SessionFactory
from app.infrastructure.llm.openrouter import OpenRouterProvider
from app.infrastructure.repositories.topics import TopicRepository
from app.infrastructure.sources.factory import build_source_registry
from app.infrastructure.telegram.publisher import TelegramPublisher
from app.shared.logging import get_logger
from app.shared.settings import get_settings

logger = get_logger(__name__)


def topic_job_id(topic_id: int) -> str:
    return f'topic:{topic_id}'


@dataclass(slots=True)
class SchedulerRuntime:
    scheduler: AsyncIOScheduler
    refresh_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.refresh_task is not None:
            self.refresh_task.cancel()
        self.scheduler.shutdown(wait=False)


class TopicSchedulerService:
    def __init__(self, scheduler: AsyncIOScheduler, *, misfire_grace_seconds: int) -> None:
        self._scheduler = scheduler
        self._misfire_grace_seconds = misfire_grace_seconds

    def upsert_topic_job(self, *, topic_id: int, hour: int, minute: int, timezone: str) -> None:
        trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)
        self._scheduler.add_job(
            process_topic_job,
            trigger=trigger,
            kwargs={'topic_id': topic_id},
            id=topic_job_id(topic_id),
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=self._misfire_grace_seconds,
        )
        job = self._scheduler.get_job(topic_job_id(topic_id))
        next_run_time = getattr(job, 'next_run_time', None) if job is not None else None
        next_run = next_run_time.isoformat() if next_run_time is not None else None
        logger.info(
            'scheduler_job_upserted',
            topic_id=topic_id,
            hour=hour,
            minute=minute,
            timezone=timezone,
            next_run_time=next_run,
        )

    def remove_topic_job(self, topic_id: int) -> None:
        try:
            self._scheduler.remove_job(job_id=topic_job_id(topic_id))
            logger.info('scheduler_job_removed', topic_id=topic_id)
        except Exception:
            pass

    def existing_topic_ids(self) -> set[int]:
        ids: set[int] = set()
        for job in self._scheduler.get_jobs():
            if not job.id.startswith('topic:'):
                continue
            try:
                ids.add(int(job.id.split(':', 1)[1]))
            except ValueError:
                continue
        return ids


async def _notify_scheduled_failure(*, topic_id: int, error_name: str) -> None:
    settings = get_settings()
    async with SessionFactory() as session:
        repo = TopicRepository(session)
        topic = await repo.get_by_id(topic_id)
        if topic is None or topic.channel is None:
            return
        bot = Bot(token=settings.bot_token)
        try:
            await bot.send_message(
                chat_id=topic.channel.telegram_chat_id,
                text=(
                    f'Автозапуск темы «{topic.query_text}» завершился с ошибкой.\n'
                    f'Техническая деталь: {error_name}'
                ),
            )
        finally:
            await bot.session.close()


async def process_topic_job(topic_id: int) -> None:
    settings = get_settings()
    logger.info('scheduler_job_started', topic_id=topic_id, started_at=datetime.now().isoformat())
    bot = Bot(token=settings.bot_token)
    try:
        async with SessionFactory() as session:
            service = TopicProcessingService(
                session=session,
                source_registry=build_source_registry(),
                llm_provider=OpenRouterProvider(),
                publisher=TelegramPublisher(bot),
            )
            outcome = await service.process_topic(topic_id=topic_id, force=False)
            logger.info(
                'scheduler_job_finished',
                topic_id=topic_id,
                found_articles=outcome.found_articles,
                unique_stories=outcome.unique_stories,
                sent_count=outcome.sent_count,
            )
    except Exception as exc:
        logger.exception('scheduler_job_failed', topic_id=topic_id, error_type=type(exc).__name__)
        await _notify_scheduled_failure(topic_id=topic_id, error_name=type(exc).__name__)
    finally:
        await bot.session.close()


async def sync_jobs(service: TopicSchedulerService) -> None:
    async with SessionFactory() as session:
        repo = TopicRepository(session)
        topics = await repo.list_active()

    active_ids: set[int] = set()
    for topic in topics:
        active_ids.add(topic.id)
        service.upsert_topic_job(
            topic_id=topic.id,
            hour=topic.delivery_time.hour,
            minute=topic.delivery_time.minute,
            timezone=topic.timezone,
        )
        now_local = datetime.now(ZoneInfo(topic.timezone))
        logger.info(
            'scheduler_topic_seen',
            topic_id=topic.id,
            query_text=topic.query_text,
            now_local=now_local.isoformat(),
            delivery_time=topic.delivery_time.strftime('%H:%M'),
            timezone=topic.timezone,
        )

    for topic_id in service.existing_topic_ids() - active_ids:
        service.remove_topic_job(topic_id)


async def _refresh_loop(service: TopicSchedulerService, interval_seconds: int) -> None:
    while True:
        try:
            await sync_jobs(service)
        except Exception:
            logger.exception('scheduler_sync_failed')
        await asyncio.sleep(interval_seconds)


async def build_scheduler_runtime() -> SchedulerRuntime:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone='UTC')
    service = TopicSchedulerService(
        scheduler,
        misfire_grace_seconds=settings.scheduler_job_misfire_grace_seconds,
    )
    await sync_jobs(service)
    refresh_task = asyncio.create_task(_refresh_loop(service, settings.scheduler_refresh_seconds))
    return SchedulerRuntime(scheduler=scheduler, refresh_task=refresh_task)
