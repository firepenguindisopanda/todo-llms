from typing import Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# local cache for client
_redis: Optional[object] = None


def get_redis_client() -> Optional[object]:
    """Return an Upstash Redis client if available and configured, otherwise None.
    Import is done lazily so the app can run without the package installed.
    """
    global _redis
    if _redis is not None:
        return _redis

    # Try to import Upstash client lazily
    try:
        from upstash_redis import Redis  # type: ignore
    except Exception as e:
        logger.debug("upstash_redis not available: %s", e)
        return None

    url = settings.UPSTASH_REDIS_REST_URL
    token = settings.UPSTASH_REDIS_REST_TOKEN
    if not url or not token:
        return None

    # Upstash Redis client (REST mode) expects url and token
    _redis = Redis(url=url, token=token)
    return _redis


# FastAPI dependency
from fastapi import Depends


def get_redis() -> Optional[object]:
    return get_redis_client()
