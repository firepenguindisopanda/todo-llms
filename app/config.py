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
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_PRICE_ID: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_SUCCESS_URL: Optional[str] = None
    STRIPE_CANCEL_URL: Optional[str] = None

    # Pusher
    PUSHER_APP_ID: Optional[str] = None
    PUSHER_KEY: Optional[str] = None
    PUSHER_SECRET: Optional[str] = None
    PUSHER_CLUSTER: Optional[str] = None

    # Redis (Upstash)
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # NVIDIA NIM LLM Configuration
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL_NAME: str = "meta/llama3-70b-instruct"
    NVIDIA_MAX_COMPLETION_TOKENS: int = 1024  # Use this for future compatibility
    NVIDIA_MAX_TOKENS: int = 1024  # Deprecated, use NVIDIA_MAX_COMPLETION_TOKENS
    NVIDIA_TEMPERATURE: float = 0.3
    NVIDIA_TIMEOUT: int = 60

    # Rate Limiting for LLM
    LLM_RATE_LIMIT_HOURLY: int = 10
    LLM_RATE_LIMIT_DAILY: int = 50
    LLM_RATE_LIMIT_MONTHLY: int = 500

    # Steps Generation
    STEPS_GENERATION_ENABLED: bool = True
    STEPS_MAX_STEPS_PER_TODO: int = 10

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
