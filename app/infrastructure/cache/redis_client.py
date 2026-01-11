from typing import Optional
from upstash_redis import Redis
from app.config import settings

_redis: Optional[Redis] = None


def get_redis_client() -> Optional[Redis]:
    global _redis
    if _redis is not None:
        return _redis

    url = settings.UPSTASH_REDIS_REST_URL
    token = settings.UPSTASH_REDIS_REST_TOKEN
    if not url or not token:
        return None

    # Upstash Redis client (REST mode) expects url and token
    _redis = Redis(url=url, token=token)
    return _redis


# FastAPI dependency
from fastapi import Depends


def get_redis() -> Optional[Redis]:
    return get_redis_client()
