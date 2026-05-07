from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobStatus
from app.infrastructure.db.models import JobRun


class JobRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, topic_id: int) -> JobRun:
        model = JobRun(
            topic_id=topic_id,
            run_id=uuid4().hex[:8],
            status=JobStatus.RUNNING.value,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def finish_success(
        self,
        job_run: JobRun,
        *,
        found_articles: int,
        unique_stories: int,
        sent_count: int,
        counters: dict[str, object] | None = None,
    ) -> None:
        job_run.finished_at = datetime.now(tz=timezone.utc)
        job_run.status = JobStatus.SUCCESS.value
        job_run.found_articles = found_articles
        job_run.unique_stories = unique_stories
        job_run.sent_count = sent_count
        job_run.counters = counters

    async def finish_failed(
        self,
        job_run: JobRun,
        *,
        error_text: str,
        counters: dict[str, object] | None = None,
    ) -> None:
        job_run.finished_at = datetime.now(tz=timezone.utc)
        job_run.status = JobStatus.FAILED.value
        job_run.error_text = error_text
        job_run.counters = counters
