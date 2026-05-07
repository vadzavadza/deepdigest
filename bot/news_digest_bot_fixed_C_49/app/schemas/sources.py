from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.domain.enums import SourceType


class RawSourceItem(BaseModel):
    source_type: SourceType = SourceType.WEB_SEARCH
    provider: str
    external_id: str | None = None
    url: HttpUrl | None = None
    title: str | None = None
    text: str | None = None
    description: str | None = None
    source_name: str
    source_language: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedSourceItem(BaseModel):
    source_type: SourceType
    provider: str
    external_id: str | None = None
    url: HttpUrl | None = None
    title: str = Field(min_length=3)
    text: str | None = None
    description: str | None = None
    source_name: str
    source_language: str | None = None
    published_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    normalized_title: str
    canonical_key: str


class StoryCandidate(BaseModel):
    story_hash: str
    canonical_title: str
    articles: list[NormalizedSourceItem]
