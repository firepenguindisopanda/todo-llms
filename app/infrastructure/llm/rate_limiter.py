"""Enhanced Rate Limiting for LLM Features

Provides user-based rate limiting for LLM API calls.
Integrates with Redis for persistent state across restarts.
"""

import time
import json
from typing import Optional, Dict
from datetime import datetime, timedelta

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.infrastructure.cache.redis_client import get_redis_client
from app.logging_config import logger


class UserBasedRateLimiter:
    """User-based rate limiter for LLM API calls.

    Features:
    - Per-user quotas (hourly, daily, monthly)
    - Redis-backed persistent state
    - Automatic quota resets
    - Graceful fallbacks
    - Integration with SlowAPI
    """

    def __init__(self):
        self.redis_client = None

    async def _get_redis(self):
        """Get Redis client."""
        if self.redis_client is None:
            self.redis_client = get_redis_client()
        return self.redis_client

    async def get_user_key(self, user_id: int, period: str) -> str:
        """Generate Redis key for user rate limiting.

        Args:
            user_id: User identifier
            period: Time period ('hourly', 'daily', 'monthly')

        Returns:
            Redis key string
        """
        now = datetime.utcnow()

        if period == "hourly":
            hour_key = now.strftime("%Y%m%d%H")
            return f"llm_rate_limit:{user_id}:hourly:{hour_key}"
        elif period == "daily":
            day_key = now.strftime("%Y%m%d")
            return f"llm_rate_limit:{user_id}:daily:{day_key}"
        elif period == "monthly":
            month_key = now.strftime("%Y%m")
            return f"llm_rate_limit:{user_id}:monthly:{month_key}"
        else:
            raise ValueError(f"Invalid period: {period}")

    async def check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded their rate limits.

        Args:
            user_id: User identifier

        Returns:
            True if within limits, False if exceeded
        """
        redis = await self._get_redis()
        if not redis:
            # Fallback to allowing requests if Redis unavailable
            logger.warning("Redis unavailable for rate limiting - allowing request")
            return True

        try:
            # Check hourly limit
            if not await self._check_period_limit(
                redis, user_id, "hourly", settings.LLM_RATE_LIMIT_HOURLY
            ):
                return False

            # Check daily limit
            if not await self._check_period_limit(
                redis, user_id, "daily", settings.LLM_RATE_LIMIT_DAILY
            ):
                return False

            # Check monthly limit
            if not await self._check_period_limit(
                redis, user_id, "monthly", settings.LLM_RATE_LIMIT_MONTHLY
            ):
                return False

            return True

        except Exception as exc:
            logger.error(f"Rate limit check failed: {exc}")
            return True  # Allow request on error

    async def _check_period_limit(
        self, redis, user_id: int, period: str, limit: int
    ) -> bool:
        """Check if user has exceeded limit for a specific time period.

        Args:
            redis: Redis client
            user_id: User identifier
            period: Time period
            limit: Maximum allowed requests

        Returns:
            True if within limit, False if exceeded
        """
        key = await self.get_user_key(user_id, period)
        current_count = redis.get(key)

        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        if current_count >= limit:
            logger.warning(
                f"User {user_id} exceeded {period} limit: {current_count}/{limit}"
            )
            return False

        return True

    async def increment_usage(self, user_id: int) -> None:
        """Increment usage counters for all time periods.

        Args:
            user_id: User identifier
        """
        redis = await self._get_redis()
        if not redis:
            return

        try:
            # Increment counters for all periods
            periods = ["hourly", "daily", "monthly"]

            for period in periods:
                key = await self.get_user_key(user_id, period)

                # Increment counter with expiration
                pipe = redis.pipeline()
                pipe.incr(key)

                # Set expiration based on period
                if period == "hourly":
                    pipe.expire(key, 3600)  # 1 hour
                elif period == "daily":
                    pipe.expire(key, 86400)  # 24 hours
                elif period == "monthly":
                    pipe.expire(key, 2592000)  # 30 days

                # Execute the pipeline
                await pipe.execute()

            logger.info(f"Incremented LLM usage for user {user_id}")

        except Exception as exc:
            logger.error(f"Failed to increment usage: {exc}")

    async def get_usage_stats(self, user_id: int) -> Dict[str, Dict[str, int]]:
        """Get current usage statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with usage statistics
        """
        redis = await self._get_redis()
        if not redis:
            return {}

        try:
            stats = {}
            periods = ["hourly", "daily", "monthly"]
            limits = {
                "hourly": settings.LLM_RATE_LIMIT_HOURLY,
                "daily": settings.LLM_RATE_LIMIT_DAILY,
                "monthly": settings.LLM_RATE_LIMIT_MONTHLY,
            }

            for period in periods:
                key = await self.get_user_key(user_id, period)
                current_count = redis.get(key)

                if current_count is None:
                    current_count = 0
                else:
                    current_count = int(current_count)

                stats[period] = {
                    "current": current_count,
                    "limit": limits[period],
                    "remaining": max(0, limits[period] - current_count),
                }

            return stats

        except Exception as exc:
            logger.error(f"Failed to get usage stats: {exc}")
            return {}


# Enhanced limiter that uses user-based limits
def get_user_id_from_request(request) -> Optional[int]:
    """Extract user ID from request for rate limiting."""
    # Try to get user from JWT token
    try:
        from app.infrastructure.security.jwt_handler import decode_token

        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            payload = decode_token(token)
            return int(payload.get("sub"))
    except Exception:
        pass

    # Fallback to IP-based limiting
    return None


async def user_rate_limit_check(request, limit: str) -> bool:
    """Check if request should be allowed based on user rate limits.

    Args:
        request: FastAPI request object
        limit: Limit identifier string

    Returns:
        True if allowed, False if rate limited
    """
    user_id = get_user_id_from_request(request)

    if user_id is not None:
        # User-based rate limiting
        limiter = UserBasedRateLimiter()
        return await limiter.check_rate_limit(user_id)
    else:
        # Fallback to IP-based rate limiting for anonymous users
        return True  # Allow anonymous requests for now


# Initialize enhanced limiter
enhanced_limiter = Limiter(key_func=get_remote_address, default_limits=["10/hour"])
