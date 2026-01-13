from fastapi import APIRouter, Request, Form, status, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies.database import get_db
from app.web.helpers import get_user_from_cookie
from app.infrastructure.database.models.user_model import User as UserModel
from app.config import settings
from app.infrastructure.cache.redis_client import get_redis_client

router = APIRouter(prefix="/cookies")


@router.post('/consent')
async def set_consent(request: Request, action: str = Form(...), db: AsyncSession = Depends(get_db), user: Optional[UserModel] = Depends(get_user_from_cookie)):
    # Accept 'accept' or 'decline'
    action = (action or '').lower()
    if action not in ('accept', 'decline'):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "invalid action"})

    # set cookie on response
    resp = JSONResponse({"status": "ok", "action": action})
    # one year
    max_age = 365 * 24 * 60 * 60
    resp.set_cookie("cookie_consent", action, max_age=max_age, samesite="lax", secure=not settings.DEBUG)

    # update user preference if logged in
    if user is not None and db is not None:
        try:
            prefs = user.preferences or {}
            prefs['cookie_consent'] = action
            user.preferences = prefs
            await db.flush()
            await db.commit()
            # invalidate cache if redis
            redis = get_redis_client()
            try:
                if redis:
                    redis.delete(f"user:{user.id}")
            except Exception:
                pass
        except Exception:
            pass

    return resp
