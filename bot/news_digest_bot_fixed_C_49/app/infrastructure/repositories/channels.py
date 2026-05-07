from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Channel


class ChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_chat_id(self, telegram_chat_id: int) -> Channel | None:
        result = await self._session.execute(
            select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()
