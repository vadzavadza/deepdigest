from datetime import datetime

from app.domain.enums import SourceType
from app.schemas.sources import RawSourceItem


class MockSourceAdapter:
    name = "mock_source"
    source_type = SourceType.WEB_SITE

    def __init__(self, items: list[RawSourceItem] | None = None) -> None:
        self._items = items or []

    async def fetch(
        self,
        query: str,
        from_dt: datetime,
        to_dt: datetime,
        limit: int,
    ) -> list[RawSourceItem]:
        filtered = [
            item
            for item in self._items
            if item.published_at is not None
            and from_dt <= item.published_at <= to_dt
            and query.lower() in (item.title or "").lower()
        ]
        return filtered[:limit]
