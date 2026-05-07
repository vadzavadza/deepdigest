from typing import Protocol
from datetime import datetime

from app.domain.enums import SourceType
from app.schemas.sources import RawSourceItem


class SourceAdapter(Protocol):
    name: str
    source_type: SourceType

    async def fetch(
        self,
        query: str,
        from_dt: datetime,
        to_dt: datetime,
        limit: int,
    ) -> list[RawSourceItem]:
        ...
