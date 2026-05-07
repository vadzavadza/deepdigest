from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import SentStory, Story
from app.domain.policies.normalization import normalize_title
from urllib.parse import urlparse


class SentStoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_recent_story_hash_ids(
        self,
        *,
        topic_id: int,
        memory_days: int,
    ) -> set[int]:
        threshold = datetime.now(tz=timezone.utc) - timedelta(days=memory_days)
        result = await self._session.execute(
            select(SentStory.story_id).where(
                SentStory.topic_id == topic_id,
                SentStory.sent_at >= threshold,
            )
        )
        return set(result.scalars().all())


    async def has_any_for_topic(self, *, topic_id: int) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(SentStory).where(SentStory.topic_id == topic_id)
        )
        return (result.scalar_one() or 0) > 0



    async def get_last_sent_at(self, *, topic_id: int) -> datetime | None:
        result = await self._session.execute(
            select(func.max(SentStory.sent_at)).where(SentStory.topic_id == topic_id)
        )
        return result.scalar_one_or_none()

    async def get_recent_sent_count(self, *, topic_id: int, hours: int = 72) -> int:
        threshold = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
        result = await self._session.execute(
            select(func.count()).select_from(SentStory).where(
                SentStory.topic_id == topic_id,
                SentStory.sent_at >= threshold,
            )
        )
        return int(result.scalar_one() or 0)

    async def get_all_story_ids(self, *, topic_id: int) -> set[int]:
        result = await self._session.execute(
            select(SentStory.story_id).where(SentStory.topic_id == topic_id)
        )
        return set(result.scalars().all())

    async def add(
        self,
        *,
        topic_id: int,
        story_id: int,
        primary_article_id: int | None,
        primary_url: str | None,
        sent_type: str,
    ) -> SentStory:
        model = SentStory(
            topic_id=topic_id,
            story_id=story_id,
            primary_article_id=primary_article_id,
            primary_url=primary_url,
            sent_type=sent_type,
        )
        self._session.add(model)
        await self._session.flush()
        return model


    async def get_sent_story_signatures(self, *, topic_id: int) -> set[str]:
        result = await self._session.execute(
            select(Story.canonical_title)
            .join(SentStory, SentStory.story_id == Story.id)
            .where(SentStory.topic_id == topic_id)
        )
        signatures: set[str] = set()
        for title in result.scalars().all():
            if title:
                signatures.add(normalize_title(title))
        return signatures

    async def get_sent_url_fingerprints(self, *, topic_id: int) -> set[str]:
        result = await self._session.execute(
            select(SentStory.primary_url).where(SentStory.topic_id == topic_id)
        )
        fingerprints: set[str] = set()
        for raw_url in result.scalars().all():
            if not raw_url:
                continue
            parsed = urlparse(str(raw_url))
            host = parsed.netloc.lower()
            path = parsed.path.rstrip('/').lower()
            if host:
                fingerprints.add(f'{host}{path}')
        return fingerprints
