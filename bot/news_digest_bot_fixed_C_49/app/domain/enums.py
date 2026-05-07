from enum import StrEnum


class OutputLanguage(StrEnum):
    EN = "en"
    DE = "de"


class DeliveryMode(StrEnum):
    LATEST = "latest"
    DAILY_DIGEST = "daily_digest"


class SentType(StrEnum):
    NEW = "new"
    UPDATE = "update"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class StoryStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class RelevanceLabel(StrEnum):
    RELEVANT = "relevant"
    WEAK = "weak"
    REJECT = "reject"


class SourceType(StrEnum):
    WEB_SEARCH = "web_search"
    WEB_SITE = "web_site"
    RSS = "rss"
    TELEGRAM_CHANNEL = "telegram_channel"
    CUSTOM_SITE = "custom_site"
    OTHER = "other"
