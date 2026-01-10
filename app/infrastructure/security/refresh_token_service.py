import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.refresh_token_model import RefreshToken as RefreshTokenModel
from app.config import settings


def _utcnow() -> datetime:
    """Get current time with timezone info (UTC)."""
    return datetime.now(timezone.utc)


async def create_refresh_token(session: AsyncSession, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    rt = RefreshTokenModel(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(rt)
    await session.flush()
    await session.commit()
    await session.refresh(rt)

    return token


async def verify_and_rotate_refresh_token(session: AsyncSession, token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await session.execute(select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if rt is None:
        return None
    now = _utcnow()
    if rt.expires_at < now or rt.revoked_at is not None:
        return None

    # Revoke old token
    rt.revoked_at = now
    await session.flush()

    # Create new token
    new_token = secrets.token_urlsafe(32)
    new_hash = hashlib.sha256(new_token.encode()).hexdigest()
    new_expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_rt = RefreshTokenModel(user_id=rt.user_id, token_hash=new_hash, expires_at=new_expires)
    session.add(new_rt)
    await session.commit()
    await session.refresh(new_rt)

    return rt.user_id, new_token


async def revoke_refresh_token(session: AsyncSession, token: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await session.execute(select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if rt is None:
        return False
    rt.revoked_at = _utcnow()
    await session.commit()
    return True
