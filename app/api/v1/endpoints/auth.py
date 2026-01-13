from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.security.jwt_handler import create_access_token, decode_token
from app.api.v1.schemas.user_schemas import UserCreate, UserOut
from app.api.dependencies.database import get_db
from app.infrastructure.database.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.application.use_cases.user.register_user import register_user
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.models.user_model import User as UserModel
from sqlalchemy import select

router = APIRouter()


@router.get('/me')
async def me(request: Request, db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    """Return current user data quickly by using cache. Authorization should be 'Bearer <token>'"""
    auth = request.headers.get('authorization')
    user_id = None
    if auth and auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1]
        try:
            payload = decode_token(token)
            user_id = int(payload.get('sub'))
        except Exception:
            user_id = None

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    cache_key = f'user:{user_id}'
    if redis:
        try:
            cached = redis.get(cache_key)
            if cached:
                import json

                return json.loads(cached)
        except Exception:
            pass

    # fall back to DB
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    view = {"id": user.id, "email": user.email, "role": user.role, "preferences": user.preferences}

    if redis:
        try:
            import json

            redis.set(cache_key, json.dumps(view), ex=300)  # TTL 5 minutes
        except Exception:
            pass

    return view


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login", response_model=Token)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> Any:
    # Per-account lockout and per-IP rate limiting protect this endpoint.
    # Check the actual user model so we can update counters and locked_until.
    from app.infrastructure.database.models.user_model import User as UserModel
    from sqlalchemy import select, update
    from datetime import datetime, timedelta, timezone
    from app.infrastructure.security.password_hasher import verify_password
    from app.infrastructure.security.refresh_token_service import create_refresh_token

    result = await db.execute(select(UserModel).where(UserModel.email == payload.email))
    user_model = result.scalar_one_or_none()

    # If user doesn't exist, respond with generic credentials error (but rate limiting/IP will still apply)
    if user_model is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # if account locked - use timezone-aware datetime for comparison
    now = datetime.now(timezone.utc)
    if user_model.locked_until and user_model.locked_until > now:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account locked until {user_model.locked_until.isoformat()}")

    if not verify_password(payload.password, user_model.password_hash):
        # increment failed attempts
        user_model.failed_login_attempts = (user_model.failed_login_attempts or 0) + 1
        LOCK_THRESHOLD = 5
        LOCK_MINUTES = 15
        if user_model.failed_login_attempts >= LOCK_THRESHOLD:
            user_model.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)
            user_model.failed_login_attempts = 0
        await db.flush()
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # successful login: reset counters
    user_model.failed_login_attempts = 0
    user_model.locked_until = None
    await db.flush()
    await db.commit()

    # create tokens
    access_token = create_access_token(subject=str(user_model.id))
    refresh_token = await create_refresh_token(db, user_model.id)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    """Register a new user."""
    repo = SQLAlchemyUserRepository(db)
    try:
        user = await register_user(payload.email, payload.password, repo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return UserOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        role=user.role,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(payload: RefreshIn, db: AsyncSession = Depends(get_db)) -> Any:
    from app.infrastructure.security.refresh_token_service import verify_and_rotate_refresh_token

    result = await verify_and_rotate_refresh_token(db, payload.refresh_token)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id, new_refresh = result
    access_token = create_access_token(subject=str(user_id))

    return {"access_token": access_token, "refresh_token": new_refresh, "token_type": "bearer"}


class LogoutIn(BaseModel):
    refresh_token: str | None = None


from fastapi import Response, Request
from app.api.dependencies.auth import get_current_user
from app.infrastructure.security.refresh_token_service import revoke_refresh_token
from datetime import datetime, timezone

from app.logging_config import logger


from fastapi import Body


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutIn | None = Body(None),
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """Revoke a single refresh token. Token may be provided in body or sent as an HttpOnly cookie named 'refresh_token'."""
    token = (payload.refresh_token if payload else None) or (request.cookies.get("refresh_token") if request else None)
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No refresh token provided")

    # lookup token owner for audit logging
    from hashlib import sha256
    from app.infrastructure.database.models.refresh_token_model import RefreshToken as RefreshTokenModel
    from sqlalchemy import select

    token_hash = sha256(token.encode()).hexdigest()
    owner_id = None
    owner_email = None
    try:
        token_res = await db.execute(select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash))
        rt = token_res.scalar_one_or_none()
        if rt is not None:
            owner_id = rt.user_id
            # fetch email
            from app.infrastructure.database.models.user_model import User as UserModel
            user_res = await db.execute(select(UserModel).where(UserModel.id == owner_id))
            user = user_res.scalar_one_or_none()
            if user is not None:
                owner_email = user.email
    except Exception:
        # non-fatal; continue with revoke
        pass

    ok = await revoke_refresh_token(db, token)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    # log logout event
    ip = None
    if request is not None:
        # respect X-Forwarded-For if present
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ip = xff.split(",")[0].strip()
        elif request.client:
            ip = request.client.host
    logger.info(f"user.logout user_id={owner_id} email={owner_email} ip={ip} method={'cookie' if request and request.cookies.get('refresh_token') else 'body'})")

    # If client used cookie, instruct deletion
    if response is not None:
        response.delete_cookie("refresh_token")
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    redis=Depends(get_redis),
):
    """Revoke all refresh tokens for the current user."""
    from app.infrastructure.database.models.refresh_token_model import RefreshToken as RefreshTokenModel
    from sqlalchemy import select

    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(RefreshTokenModel).where(RefreshTokenModel.user_id == current_user.id, RefreshTokenModel.revoked_at.is_(None))
    )
    tokens = result.scalars().all()
    for t in tokens:
        t.revoked_at = now
        # set redis blacklist for each token
        try:
            if redis:
                ttl = int((t.expires_at - now).total_seconds())
                if ttl > 0:
                    redis.set(f"revoked_refresh:{t.token_hash}", "1", ex=ttl)
        except Exception:
            pass

    await db.flush()
    await db.commit()

    # log logout-all event
    ip = None
    xff = None
    try:
        xff = request.headers.get("x-forwarded-for") if request is not None else None
    except Exception:
        xff = None
    if xff:
        ip = xff.split(",")[0].strip()
    elif request is not None and request.client:
        ip = request.client.host

    logger.info(f"user.logout_all user_id={current_user.id} email={current_user.email} ip={ip}")

    return {"message": "All sessions revoked"}
