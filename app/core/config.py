from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DeepDigest"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/deepdigest"

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7   # 7 days
    ALGORITHM: str = "HS256"

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@deepdigest.app"
    EMAIL_FROM_NAME: str = "DeepDigest"

    # Frontend
    FRONTEND_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]

    # Telegram bot (for notifications)
    TELEGRAM_BOT_TOKEN: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
