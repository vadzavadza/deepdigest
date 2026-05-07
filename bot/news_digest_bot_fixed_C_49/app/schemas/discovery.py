from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import SourceType


class SourceFetchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    from_dt: datetime
    to_dt: datetime
    limit: int = Field(ge=1, le=100)


class SourceFetchStats(BaseModel):
    source_name: str
    source_type: SourceType
    fetched_count: int = 0
    failed: bool = False
    error_message: str | None = None


class SourceCollectionResult(BaseModel):
    items_count: int = 0
    stats: list[SourceFetchStats] = Field(default_factory=list)
