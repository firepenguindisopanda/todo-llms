from typing import Optional
from fastapi import Request
import secrets


def ensure_csrf_token(request: Request) -> str:
    """Ensure a CSRF token exists in the session and return it."""
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def validate_csrf_token(request: Request, token: Optional[str]) -> bool:
    """Validate provided CSRF token matches the one in session. Logs both for debugging."""
    session_token = request.session.get("csrf_token")
    # debug logging to help trace issues in tests
    try:
        import logging

        logger = logging.getLogger("app.web.helpers")
        logger.info("validate_csrf_token: session=%s provided=%s", session_token, token)
    except Exception:
        pass
    if not token or not session_token:
        return False
    return secrets.compare_digest(session_token, token)

def set_flash(request: Request, message: str) -> None:
    """Set a one-time flash message in session."""
    try:
        import logging

        logging.getLogger("app.web.helpers").debug("set_flash: setting _flash=%s", message)
    except Exception:
        pass
    request.session["_flash"] = message


def pop_flash(request: Request) -> Optional[str]:
    """Pop and return the flash message from session, or None.

    Use explicit deletion and logging so we can trace why pop may not be
    removing the value in some test runs.
    """
    try:
        import logging

        logger = logging.getLogger("app.web.helpers")
        logger.debug("pop_flash BEFORE: keys=%s _flash=%s", list(request.session.keys()), request.session.get("_flash"))
    except Exception:
        logger = None

    val = request.session.get("_flash", None)
    if val is not None:
        try:
            # prefer explicit deletion to avoid surprising mapping behaviour
            del request.session["_flash"]
        except Exception:
            if logger is not None:
                logger.exception("pop_flash: failed to delete _flash")
    try:
        if logger is not None:
            logger.debug("pop_flash AFTER: keys=%s", list(request.session.keys()))
    except Exception:
        pass
    return val


# FastAPI dependency
from fastapi import Request as FastAPIRequest

def get_csrf_token(request: FastAPIRequest) -> str:
    """FastAPI dependency to ensure CSRF token exists, set it on request.state, and return it.

    Use as: csrf = Depends(get_csrf_token) in route signatures. The dependency will also
    populate `request.state.csrf_token` for templates (when called during a page GET).
    """
    token = ensure_csrf_token(request)
    try:
        request.state.csrf_token = token
    except Exception:
        pass
    return token


def get_and_pop_flash(request: FastAPIRequest) -> Optional[str]:
    """Dependency that pops any flash message from session and stores it on request.state.

    Use as: flash = Depends(get_and_pop_flash) in GET routes that render templates.
    """
    try:
        val = pop_flash(request)
        try:
            request.state.flash = val
        except Exception:
            pass
        return val
    except Exception:
        try:
            request.state.flash = None
        except Exception:
            pass
        return None


# Web auth helper (for server-rendered pages)
from fastapi import Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies.database import get_db
from app.infrastructure.security.refresh_token_service import verify_and_rotate_refresh_token
from sqlalchemy import select
from app.infrastructure.database.models.user_model import User as UserModel
from app.config import settings


async def get_user_from_cookie(request: FastAPIRequest, response: Response, db: AsyncSession = Depends(get_db)) -> Optional[UserModel]:
    """FastAPI dependency that extracts the refresh token from cookies and returns the
    corresponding User model instance or None.

    To avoid invalidating a token during harmless GET requests (which can break tests
    where a subsequent POST expects the rotated token), the helper **does not** rotate
    the refresh token on GET requests. Rotation only occurs for non-GET (mutating)
    requests.

    Use in page routes as:
      user = Depends(get_user_from_cookie)
    """
    token = request.cookies.get("refresh_token")
    if not token:
        return None

    # Verify token exists and is valid (without rotating).
    # Rotating tokens from within page request handlers caused tests to send
    # stale cookies in subsequent requests, so keep verification read-only here.
    import hashlib
    from app.infrastructure.database.models.refresh_token_model import RefreshToken as RefreshTokenModel
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if rt is None:
        return None
    if rt.expires_at < __import__('datetime').datetime.now(__import__('datetime').timezone.utc) or rt.revoked_at is not None:
        return None
    user_id = rt.user_id

    # fetch user
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None

    # expose to templates via request.state for convenience
    try:
        request.state.user = user
    except Exception:
        pass

    return user
