from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "FastAPI Todo API"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: Optional[AnyUrl] = None

    # JWT
    JWT_SECRET_KEY: str = "changeme"
    SESSION_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Redis
    REDIS_URL: Optional[str] = None

    # Logging
    LOG_DIR: Path = Path("logs")
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    LOG_ROTATION_TYPE: str = "size"  # 'size' or 'time'
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 10
    LOG_ROTATION_WHEN: str = "midnight"  # used for time-based rotation
    LOG_COMPRESS: bool = True


settings = Settings()
