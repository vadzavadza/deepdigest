from datetime import time

from pydantic import BaseModel, Field

from app.domain.enums import DeliveryMode, OutputLanguage


class TopicCreate(BaseModel):
    query_text: str = Field(min_length=1, max_length=200)
    output_language: OutputLanguage
    delivery_time: time
    timezone: str
    mode: DeliveryMode
    channel_id: int
    is_active: bool = True


class TopicRead(TopicCreate):
    id: int
    user_id: int
