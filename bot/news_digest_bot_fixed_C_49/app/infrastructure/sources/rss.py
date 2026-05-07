from __future__ import annotations

from datetime import datetime

from app.domain.enums import SourceType
from app.schemas.sources import RawSourceItem


class RssSource:
    name = 'rss_source'
    source_type = SourceType.RSS

    async def fetch(
        self,
        query: str,
        from_dt: datetime,
        to_dt: datetime,
        limit: int,
    ) -> list[RawSourceItem]:
        raise NotImplementedError('RSS source will be connected in a later milestone.')
