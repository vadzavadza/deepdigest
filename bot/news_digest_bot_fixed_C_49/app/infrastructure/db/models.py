from datetime import time

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import JobStatus, StoryStatus
from app.infrastructure.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    locale: Mapped[str | None] = mapped_column(String(8), nullable=True)

    channels = relationship("Channel", back_populates="user")
    topics = relationship("Topic", back_populates="user")


class Channel(TimestampMixin, Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    user = relationship("User", back_populates="channels")
    topics = relationship("Topic", back_populates="channel")


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(String(200), nullable=False)
    output_language: Mapped[str] = mapped_column(String(8), nullable=False)
    delivery_time: Mapped[time] = mapped_column(Time(), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    user = relationship("User", back_populates="topics")
    channel = relationship("Channel", back_populates="topics")
    stories = relationship("Story", back_populates="topic")


class Article(TimestampMixin, Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("provider", "provider_external_id", name="uq_articles_provider_external_id"),
        UniqueConstraint("url", name="uq_articles_url"),
        Index("ix_articles_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    published_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


class Story(Base):
    __tablename__ = "stories"
    __table_args__ = (
        UniqueConstraint("topic_id", "story_hash", name="uq_stories_topic_story_hash"),
        Index("ix_stories_story_hash", "story_hash"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False, index=True)
    story_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_title: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=StoryStatus.ACTIVE.value)

    topic = relationship("Topic", back_populates="stories")
    story_articles = relationship("StoryArticle", back_populates="story")
    sent_stories = relationship("SentStory", back_populates="story")


class StoryArticle(Base):
    __tablename__ = "story_articles"
    __table_args__ = (
        UniqueConstraint("story_id", "article_id", name="uq_story_articles_story_article"),
    )

    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    score: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    story = relationship("Story", back_populates="story_articles")


class SentStory(Base):
    __tablename__ = "sent_stories"
    __table_args__ = (
        UniqueConstraint("topic_id", "story_id", "sent_type", name="uq_sent_stories_business"),
        Index("ix_sent_stories_sent_at", "sent_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False, index=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), nullable=False, index=True)
    primary_article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"), nullable=True)
    primary_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sent_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    story = relationship("Story", back_populates="sent_stories")


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = (Index("ix_job_runs_topic_id_started_at", "topic_id", "started_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    started_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.PENDING.value)
    found_articles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unique_stories: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    counters: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
