from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
from app.models.user import Plan


# ── AUTH ──────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


# ── USER ──────────────────────────────────────────────
class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_verified: bool
    plan: Plan
    language: str
    telegram_chat_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    language: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
