from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import OutputLanguage, SentType


@dataclass(slots=True, frozen=True)
class ProcessingWindow:
    from_dt: datetime
    to_dt: datetime


@dataclass(slots=True, frozen=True)
class RankedStory:
    story_hash: str
    canonical_title: str
    score: float
    primary_url: str
    source_name: str
    source_language: str | None
    published_at: datetime
    summary: str | None = None
    sent_type: SentType = SentType.NEW
    output_language: OutputLanguage = OutputLanguage.EN
