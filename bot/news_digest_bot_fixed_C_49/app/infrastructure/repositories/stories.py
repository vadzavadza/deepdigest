from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Story


class StoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, *, topic_id: int, story_hash: str) -> Story | None:
        result = await self._session.execute(
            select(Story).where(Story.topic_id == topic_id, Story.story_hash == story_hash)
        )
        return result.scalar_one_or_none()

    async def upsert_story(
        self,
        *,
        topic_id: int,
        story_hash: str,
        canonical_title: str,
        first_seen_at: datetime,
        last_seen_at: datetime,
    ) -> Story:
        existing = await self.get_by_hash(topic_id=topic_id, story_hash=story_hash)
        if existing is not None:
            existing.last_seen_at = max(existing.last_seen_at, last_seen_at)
            if not existing.canonical_title:
                existing.canonical_title = canonical_title
            return existing

        model = Story(
            topic_id=topic_id,
            story_hash=story_hash,
            canonical_title=canonical_title,
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model
