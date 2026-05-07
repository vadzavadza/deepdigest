from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import Topic


class TopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, topic_id: int) -> Topic | None:
        result = await self._session.execute(
            select(Topic).options(selectinload(Topic.channel)).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Topic]:
        result = await self._session.execute(
            select(Topic).options(selectinload(Topic.channel)).where(Topic.is_active.is_(True))
        )
        return list(result.scalars().all())
