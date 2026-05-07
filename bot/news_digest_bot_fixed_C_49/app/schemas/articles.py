from datetime import datetime

from pydantic import Field, HttpUrl

from app.domain.enums import SourceType
from app.schemas.sources import NormalizedSourceItem, RawSourceItem, StoryCandidate


class RawArticle(RawSourceItem):
    source_type: SourceType = SourceType.WEB_SITE
    url: HttpUrl
    title: str = Field(min_length=3)
    published_at: datetime


class NormalizedArticle(NormalizedSourceItem):
    source_type: SourceType = SourceType.WEB_SITE
    url: HttpUrl


__all__ = [
    "RawArticle",
    "NormalizedArticle",
    "RawSourceItem",
    "NormalizedSourceItem",
    "StoryCandidate",
]
