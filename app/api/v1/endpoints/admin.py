from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_active_admin
from app.infrastructure.database.models.user_model import User as UserModel
from app.infrastructure.database.models.refresh_token_model import RefreshToken as RefreshTokenModel

router = APIRouter()


def _utcnow() -> datetime:
    """Get current time with timezone info (UTC)."""
    return datetime.now(timezone.utc)


# ---------- Schemas ----------

class RefreshTokenOut(BaseModel):
    id: int
    user_id: int
    user_email: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime]
    is_active: bool


class PaginatedRefreshTokens(BaseModel):
    items: List[RefreshTokenOut]
    total: int
    page: int
    page_size: int
    pages: int


class UserOut(BaseModel):
    id: int
    email: str
    is_active: bool
    role: str


class PaginatedUsers(BaseModel):
    items: List[UserOut]
    total: int
    page: int
    page_size: int
    pages: int


# ---------- Endpoints ----------

@router.get("/users", response_model=PaginatedUsers)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Depends(get_current_active_admin),
):
    """List all users (admin only)."""
    # Count
    count_result = await db.execute(select(UserModel))
    all_users = count_result.scalars().all()
    total = len(all_users)

    # Paginate
    offset = (page - 1) * page_size
    stmt = select(UserModel).order_by(UserModel.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total else 1

    return PaginatedUsers(
        items=[
            UserOut(id=u.id, email=u.email, is_active=u.is_active, role=u.role)
            for u in users
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/refresh-tokens", response_model=PaginatedRefreshTokens)
async def list_refresh_tokens(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    active_only: bool = Query(False, description="Only show active (non-revoked, non-expired) tokens"),
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Depends(get_current_active_admin),
):
    """List all refresh tokens (admin only). Optionally filter by user or active status."""
    stmt = select(RefreshTokenModel)
    if user_id is not None:
        stmt = stmt.where(RefreshTokenModel.user_id == user_id)

    result = await db.execute(stmt)
    all_tokens = result.scalars().all()

    # Filter active if requested
    now = _utcnow()
    if active_only:
        all_tokens = [t for t in all_tokens if t.revoked_at is None and t.expires_at > now]

    total = len(all_tokens)

    # Paginate (in-memory for simplicity; for large datasets, do this in SQL)
    offset = (page - 1) * page_size
    tokens = all_tokens[offset : offset + page_size]

    # Fetch user emails for display
    user_ids = list(set(t.user_id for t in tokens))
    users_result = await db.execute(select(UserModel).where(UserModel.id.in_(user_ids)))
    users_map = {u.id: u.email for u in users_result.scalars().all()}

    pages = (total + page_size - 1) // page_size if total else 1

    return PaginatedRefreshTokens(
        items=[
            RefreshTokenOut(
                id=t.id,
                user_id=t.user_id,
                user_email=users_map.get(t.user_id),
                created_at=t.created_at,
                expires_at=t.expires_at,
                revoked_at=t.revoked_at,
                is_active=(t.revoked_at is None and t.expires_at > now),
            )
            for t in tokens
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.delete("/refresh-tokens/{token_id}", status_code=204)
async def revoke_refresh_token(
    token_id: int,
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Depends(get_current_active_admin),
):
    """Revoke a specific refresh token by ID (admin only)."""
    result = await db.execute(select(RefreshTokenModel).where(RefreshTokenModel.id == token_id))
    token = result.scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refresh token not found")

    if token.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token already revoked")

    token.revoked_at = _utcnow()
    await db.flush()
    await db.commit()
    return None


@router.delete("/refresh-tokens/user/{user_id}", status_code=204)
async def revoke_all_user_tokens(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Depends(get_current_active_admin),
):
    """Revoke all refresh tokens for a specific user (admin only)."""
    # Verify user exists
    user_result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Revoke all non-revoked tokens
    result = await db.execute(
        select(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.revoked_at.is_(None),
        )
    )
    tokens = result.scalars().all()
    now = _utcnow()
    for t in tokens:
        t.revoked_at = now

    await db.flush()
    await db.commit()
    return None


@router.put("/users/{user_id}/deactivate", status_code=200)
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Depends(get_current_active_admin),
):
    """Deactivate a user account and revoke all their tokens (admin only)."""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")

    user.is_active = False

    # Revoke all tokens
    tokens_result = await db.execute(
        select(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.revoked_at.is_(None),
        )
    )
    tokens = tokens_result.scalars().all()
    now = _utcnow()
    for t in tokens:
        t.revoked_at = now

    await db.flush()
    await db.commit()

    return {"message": f"User {user.email} deactivated and all tokens revoked"}


@router.put("/users/{user_id}/activate", status_code=200)
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Depends(get_current_active_admin),
):
    """Reactivate a user account (admin only)."""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = True
    await db.flush()
    await db.commit()

    return {"message": f"User {user.email} activated"}
