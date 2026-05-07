from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.domain.enums import DeliveryMode, OutputLanguage, SentType


class StorySummary(BaseModel):
    story_hash: str
    title: str
    summary: str
    primary_url: HttpUrl
    source_name: str
    source_language: str
    is_update: bool = False


class PublishStoryItem(BaseModel):
    title: str
    summary: str
    source_name: str
    source_language: str
    link: HttpUrl
    sent_type: SentType = SentType.NEW


class PublishPayload(BaseModel):
    topic_id: int
    query_text: str
    output_language: OutputLanguage
    mode: DeliveryMode
    generated_at: datetime
    items: list[PublishStoryItem] = Field(default_factory=list)
