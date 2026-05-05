from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import enum

from app.db.base import Base


class Plan(str, enum.Enum):
    free = "free"
    pro = "pro"
    team = "team"


class User(Base):
    __tablename__ = "users"

    id:               Mapped[int]      = mapped_column(primary_key=True, index=True)
    email:            Mapped[str]      = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password:  Mapped[str]      = mapped_column(String(255), nullable=False)
    is_verified:      Mapped[bool]     = mapped_column(Boolean, default=False)
    is_active:        Mapped[bool]     = mapped_column(Boolean, default=True)
    plan:             Mapped[Plan]     = mapped_column(SAEnum(Plan), default=Plan.free)
    telegram_chat_id: Mapped[str|None] = mapped_column(String(64), nullable=True)
    language:         Mapped[str]      = mapped_column(String(8), default="en")
    created_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
