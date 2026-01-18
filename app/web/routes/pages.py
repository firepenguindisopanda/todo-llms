from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from app.main import templates
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.api.dependencies.database import get_db
from app.infrastructure.database.models.todo_model import Todo as TodoModel
from app.infrastructure.database.models.user_model import User as UserModel
from app.web.helpers import (
    get_csrf_token,
    get_and_pop_flash,
    get_user_from_cookie,
    validate_csrf_token,
    set_flash,
)
from app.infrastructure.cache.redis_client import get_redis

router = APIRouter()


@router.post("/todos/{todo_id}/delete")
async def delete_todo(
    request: Request,
    todo_id: int,
    csrf_token: str = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
):
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )
    # CSRF validation
    if not validate_csrf_token(request, csrf_token):
        set_flash(request, "Invalid CSRF token")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    todo = await db.get(TodoModel, todo_id)
    if not todo or todo.user_id != user.id:
        set_flash(request, "Todo not found or unauthorized")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    await db.delete(todo)
    await db.commit()
    set_flash(request, "Todo deleted successfully.")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/todos/{todo_id}/complete")
async def complete_todo(
    request: Request,
    todo_id: int,
    csrf_token: str = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
):
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )
    # CSRF validation
    if not validate_csrf_token(request, csrf_token):
        set_flash(request, "Invalid CSRF token")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    todo = await db.get(TodoModel, todo_id)
    if not todo or todo.user_id != user.id:
        set_flash(request, "Todo not found or unauthorized")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    if not todo.completed:
        todo.completed = True
        await db.commit()
        set_flash(request, "Todo marked as completed.")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/subscribe")
async def subscribe(request: Request, user: UserModel = Depends(get_user_from_cookie)):
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        try:
            resp = await client.post(
                "/api/v1/subscriptions/create-checkout-session",
                json={"user_id": user.id, "plan": "pro"},
            )
            resp.raise_for_status()
            data = resp.json()
            return RedirectResponse(data["url"], status_code=303)
        except Exception as e:
            import logging

            logging.getLogger("app.web.pages").error(f"Subscription error: {e}")
            set_flash(
                request,
                "Failed to initiate subscription. Please try again later.",
                category="danger",
            )
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/todos/{todo_id}/regenerate-steps")
async def regenerate_todo_steps(
    request: Request,
    todo_id: int,
    csrf_token: str = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
):
    """Regenerate AI steps for a todo."""
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )

    # CSRF validation
    if not validate_csrf_token(request, csrf_token):
        set_flash(request, "Invalid CSRF token")
        return RedirectResponse(
            url=f"/todos/{todo_id}", status_code=status.HTTP_303_SEE_OTHER
        )

    # Check rate limits
    try:
        from app.infrastructure.llm.rate_limiter import UserBasedRateLimiter

        rate_limiter = UserBasedRateLimiter()

        can_proceed = await rate_limiter.check_rate_limit(user.id)
        if not can_proceed:
            set_flash(
                request,
                "Rate limit exceeded. Please try again later.",
                category="danger",
            )
            return RedirectResponse(
                url=f"/todos/{todo_id}", status_code=status.HTTP_303_SEE_OTHER
            )

        # Regenerate steps with separate session
        async def regenerate_steps_background():
            try:
                from app.infrastructure.database.connection import get_async_session

                async for session in get_async_session():
                    from app.infrastructure.llm.todo_steps_service import (
                        TodoStepsService,
                    )

                    steps_service = TodoStepsService(session)
                    return await steps_service.regenerate_steps(todo_id, user.id)
            except Exception as exc:
                import logging

                logging.getLogger("app.web.pages").error(
                    f"Background step regeneration failed for todo {todo_id}: {exc}"
                )
                return False

        success = await regenerate_steps_background()

        if success:
            # Increment usage
            await rate_limiter.increment_usage(user.id)
            set_flash(request, "Steps regenerated successfully.")
        else:
            set_flash(
                request,
                "Failed to regenerate steps. Please try again.",
                category="danger",
            )

    except Exception as exc:
        import logging

        logging.getLogger("app.web.pages").error(f"Steps regeneration error: {exc}")
        set_flash(request, "An error occurred. Please try again.", category="danger")

    return RedirectResponse(
        url=f"/todos/{todo_id}", status_code=status.HTTP_303_SEE_OTHER
    )




@router.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    user: UserModel = Depends(get_user_from_cookie),
    csrf: str = Depends(get_csrf_token),
    flash: str = Depends(get_and_pop_flash),
):
    """Root page: redirect authenticated users to dashboard; otherwise show login page."""
    if user is not None:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    # show login page for guests
    return templates.TemplateResponse(
        request,
        "pages/auth/login.html",
        {"request": request, "current_year": datetime.utcnow().year},
    )


@router.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/home.html",
        {"request": request, "current_year": datetime.utcnow().year},
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
    csrf: str = Depends(get_csrf_token),
    flash: str = Depends(get_and_pop_flash),
):
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )

    stmt = (
        select(TodoModel)
        .where(TodoModel.user_id == user.id)
        .order_by(TodoModel.created_at.desc())
    )
    result = await db.execute(stmt)
    todos = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {"request": request, "current_year": datetime.utcnow().year, "todos": todos},
    )


@router.post("/todos/create")
async def create_todo(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    csrf_token: str = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
):
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )

    # CSRF validation
    if not validate_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "pages/dashboard.html",
            {
                "request": request,
                "error": "Invalid CSRF token",
                "title": title,
                "description": description,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Enforce free user todo limit
    if getattr(user, "subscription_status", None) != "active":
        stmt = select(TodoModel).where(TodoModel.user_id == user.id)
        result = await db.execute(stmt)
        todo_count = len(result.scalars().all())
        if todo_count >= 10:
            set_flash(
                request,
                "Free users are limited to 10 todos. Subscribe for unlimited todos.",
                category="danger",
            )
            return RedirectResponse(
                url="/dashboard", status_code=status.HTTP_303_SEE_OTHER
            )

    todo = TodoModel(user_id=user.id, title=title, description=description)
    db.add(todo)
    await db.flush()
    await db.commit()
    await db.refresh(todo)

    set_flash(request, "Todo created successfully.")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/account", response_class=HTMLResponse)
async def account_get(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
    csrf: str = Depends(get_csrf_token),
    flash: str = Depends(get_and_pop_flash),
    redis=Depends(get_redis),
):
    """Show account page with current preferences."""
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )

    prefs = user.preferences or {}
    return templates.TemplateResponse(
        request, "pages/account.html", {"request": request, "preferences": prefs}
    )


@router.post("/account")
async def account_post(
    request: Request,
    display_mode: str = Form(None),
    items_per_page: int = Form(None),
    show_email: bool = Form(False),
    profile_public: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
    csrf_token: str = Form(None),
    redis=Depends(get_redis),
):
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )

    # CSRF validation
    if not validate_csrf_token(request, csrf_token):
        set_flash(request, "Invalid CSRF token")
        return RedirectResponse(url="/account", status_code=status.HTTP_303_SEE_OTHER)

    prefs = user.preferences or {}
    if display_mode:
        prefs["display_mode"] = display_mode
    if items_per_page is not None:
        try:
            prefs["items_per_page"] = int(items_per_page)
        except Exception:
            pass

    # Social Privacy
    prefs["show_email_to_friends"] = show_email
    prefs["is_profile_public"] = profile_public

    user.preferences = prefs
    await db.flush()
    await db.commit()

    # invalidate cache
    if redis:
        try:
            cache_key = f"user:{user.id}"
            redis.delete(cache_key)
        except Exception:
            pass

    set_flash(request, "Account updated")
    return RedirectResponse(url="/account", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/friends", response_class=HTMLResponse)
async def friends_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
    csrf: str = Depends(get_csrf_token),
):
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )

    from app.application.use_cases.friends.friend_service import FriendService

    service = FriendService(db)
    friends = await service.list_friends(user.id)
    pending = await service.list_pending_received(user.id)

    # Simple formatting for friends
    formatted_friends = []
    for f in friends:
        is_online = (
            f.last_seen
            and (
                datetime.now(__import__("datetime").timezone.utc) - f.last_seen
            ).total_seconds()
            < 300
        )
        formatted_friends.append(
            {
                "id": f.id,
                "username": f.email.split("@")[0],
                "email": f.email,
                "is_online": is_online,
                "pref": f.preferences or {},
            }
        )

    from app.config import settings

    return templates.TemplateResponse(
        request,
        "pages/friends.html",
        {
            "request": request,
            "friends": formatted_friends,
            "pending": pending,
            "pusher_key": settings.PUSHER_KEY,
            "pusher_cluster": settings.PUSHER_CLUSTER,
        },
    )


@router.get("/chat/{friend_id}", response_class=HTMLResponse)
async def chat_page(
    friend_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
):
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )

    # Verify that the friend exists and is actually a friend
    from app.infrastructure.database.models.friendship_model import (
        Friendship as FriendshipModel,
        FriendshipStatus,
    )
    from sqlalchemy import and_, or_

    stmt = select(FriendshipModel).where(
        and_(
            FriendshipModel.status == FriendshipStatus.ACCEPTED,
            or_(
                and_(
                    FriendshipModel.user_id == user.id,
                    FriendshipModel.friend_id == friend_id,
                ),
                and_(
                    FriendshipModel.user_id == friend_id,
                    FriendshipModel.friend_id == user.id,
                ),
            ),
        )
    )
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        set_flash(
            request, "You can only chat with accepted friends.", category="danger"
        )
        return RedirectResponse(url="/friends", status_code=status.HTTP_303_SEE_OTHER)

    # Get friend user object
    friend_user = await db.get(UserModel, friend_id)

    from app.application.use_cases.chat.chat_service import ChatService

    chat_service = ChatService(db)
    messages = await chat_service.get_chat_history(user.id, friend_id)

    from app.config import settings

    return templates.TemplateResponse(
        request,
        "pages/chat.html",
        {
            "request": request,
            "friend": friend_user,
            "messages": messages,
            "pusher_key": settings.PUSHER_KEY,
            "pusher_cluster": settings.PUSHER_CLUSTER,
        },
    )


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
    csrf: str = Depends(get_csrf_token),
    flash: str = Depends(get_and_pop_flash),
):
    """Admin-only dashboard for system overview."""
    if user is None or user.role != "admin":
        set_flash(request, "Access denied. Admin privileges required.")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    from sqlalchemy import func

    user_count = await db.scalar(select(func.count(UserModel.id)))
    todo_count = await db.scalar(select(func.count(TodoModel.id)))

    # Latest 5 users
    latest_users = (
        (
            await db.execute(
                select(UserModel).order_by(UserModel.created_at.desc()).limit(5)
            )
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        request,
        "pages/admin_dashboard.html",
        {
            "request": request,
            "current_year": datetime.utcnow().year,
            "user_count": user_count,
            "todo_count": todo_count,
            "latest_users": latest_users,
        },
    )


@router.get("/admin/cookies", response_class=HTMLResponse)
async def admin_cookies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
    csrf: str = Depends(get_csrf_token),
    flash: str = Depends(get_and_pop_flash),
):
    """Admin page to view cookie consent settings across users."""
    if user is None or user.role != "admin":
        set_flash(request, "Access denied. Admin privileges required.")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # optional filter
    q = request.query_params.get("q")
    if q:
        users = (
            (
                await db.execute(
                    select(UserModel)
                    .where(
                        (UserModel.email.ilike(f"%{q}%"))
                        | (UserModel.role.ilike(f"%{q}%"))
                    )
                    .order_by(UserModel.created_at.desc())
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
    else:
        users = (
            (
                await db.execute(
                    select(UserModel).order_by(UserModel.created_at.desc()).limit(200)
                )
            )
            .scalars()
            .all()
        )
    return templates.TemplateResponse(
        request, "pages/admin_cookies.html", {"request": request, "users": users}
    )


@router.post("/admin/cookies/clear")
async def admin_cookies_clear(
    request: Request,
    user_id: int = Form(...),
    csrf_token: str = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
):
    """Clear cookie consent for a particular user."""
    if user is None or user.role != "admin":
        set_flash(request, "Access denied. Admin privileges required.")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    from app.web.helpers import validate_csrf_token

    if not validate_csrf_token(request, csrf_token):
        set_flash(request, "Invalid CSRF token")
        return RedirectResponse(
            url="/admin/cookies", status_code=status.HTTP_303_SEE_OTHER
        )

    # fetch target user
    res = await db.execute(select(UserModel).where(UserModel.id == user_id))
    target = res.scalar_one_or_none()
    if target is None:
        set_flash(request, "User not found")
        return RedirectResponse(
            url="/admin/cookies", status_code=status.HTTP_303_SEE_OTHER
        )

    prefs = target.preferences or {}
    # construct a new dict to avoid in-place mutation issues and ensure change detection
    new_prefs = {
        k: v
        for k, v in (prefs.items() if isinstance(prefs, dict) else [])
        if k != "cookie_consent"
    }
    if new_prefs != (prefs or {}):
        target.preferences = new_prefs
        await db.flush()
        await db.commit()
        # invalidate cache if redis
        from app.infrastructure.cache.redis_client import get_redis_client

        try:
            r = get_redis_client()
            if r:
                r.delete(f"user:{target.id}")
        except Exception:
            pass
        set_flash(request, "Consent cleared for user")
    else:
        set_flash(request, "No consent set for user")

    return RedirectResponse(url="/admin/cookies", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/cookies/bulk_clear")
async def admin_cookies_bulk_clear(
    request: Request,
    user_ids: list[int] = Form(...),
    csrf_token: str = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
):
    """Bulk clear cookie consent for a set of users (admin-only)."""
    if user is None or user.role != "admin":
        set_flash(request, "Access denied. Admin privileges required.")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    from app.web.helpers import validate_csrf_token

    if not validate_csrf_token(request, csrf_token):
        set_flash(request, "Invalid CSRF token")
        return RedirectResponse(
            url="/admin/cookies", status_code=status.HTTP_303_SEE_OTHER
        )

    # Fetch all targets
    res = await db.execute(select(UserModel).where(UserModel.id.in_(user_ids)))
    targets = res.scalars().all()

    if not targets:
        set_flash(request, "No users selected")
        return RedirectResponse(
            url="/admin/cookies", status_code=status.HTTP_303_SEE_OTHER
        )

    from app.infrastructure.database.models.audit_log_model import AuditLog
    from json import dumps

    modified = 0
    for t in targets:
        prefs = t.preferences or {}
        if "cookie_consent" in prefs:
            new_prefs = {k: v for k, v in prefs.items() if k != "cookie_consent"}
            t.preferences = new_prefs
            # audit row
            a = AuditLog(
                actor_id=user.id,
                target_user_id=t.id,
                action="clear_cookie_consent",
                details=dumps({"prev": prefs.get("cookie_consent")}),
            )
            db.add(a)
            modified += 1
            # invalidate cache
            try:
                from app.infrastructure.cache.redis_client import get_redis_client

                r = get_redis_client()
                if r:
                    r.delete(f"user:{t.id}")
            except Exception:
                pass

    if modified > 0:
        await db.flush()
        await db.commit()
        set_flash(request, f"Cleared consent for {modified} user(s)")
    else:
        set_flash(request, "No consents were set for selected users")

    return RedirectResponse(url="/admin/cookies", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/cookies/audit", response_class=HTMLResponse)
async def admin_cookies_audit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
    csrf: str = Depends(get_csrf_token),
    flash: str = Depends(get_and_pop_flash),
):
    if user is None or user.role != "admin":
        set_flash(request, "Access denied. Admin privileges required.")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    from app.infrastructure.database.models.audit_log_model import AuditLog

    audits = (
        (
            await db.execute(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)
            )
        )
        .scalars()
        .all()
    )
    return templates.TemplateResponse(
        request,
        "pages/admin_cookies_audit.html",
        {"request": request, "audits": audits},
    )


@router.get("/admin/cookies/export")
async def admin_cookies_export(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
):
    """Export users (filtered) as CSV. Admin-only."""
    if user is None or user.role != "admin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    q = request.query_params.get("q")
    if q:
        res = await db.execute(
            select(UserModel)
            .where((UserModel.email.ilike(f"%{q}%")) | (UserModel.role.ilike(f"%{q}%")))
            .order_by(UserModel.created_at.desc())
            .limit(1000)
        )
    else:
        res = await db.execute(
            select(UserModel).order_by(UserModel.created_at.desc()).limit(1000)
        )

    users = res.scalars().all()

    # build CSV
    import csv
    from io import StringIO

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["id", "email", "cookie_consent"])
    for u in users:
        prefs = u.preferences or {}
        writer.writerow(
            [
                u.id,
                u.email,
                prefs.get("cookie_consent") if isinstance(prefs, dict) else "",
            ]
        )

    from fastapi.responses import Response

    return Response(content=si.getvalue(), media_type="text/csv")


@router.get("/todos/{todo_id}", response_class=HTMLResponse)
async def todo_details(
    todo_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user_from_cookie),
    csrf: str = Depends(get_csrf_token),
    flash: str = Depends(get_and_pop_flash),
):
    """Show detailed view of a todo with AI-generated steps."""
    if user is None:
        return RedirectResponse(
            url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
        )

    # Get todo with steps (this will trigger generation if needed)
    from app.infrastructure.llm.todo_steps_service import TodoStepsService

    steps_service = TodoStepsService(db)
    todo = await steps_service.get_todo_with_steps(todo_id, user.id)

    if todo is None:
        set_flash(request, "Todo not found", category="danger")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # Get rate limit stats for UI
    try:
        from app.infrastructure.llm.rate_limiter import UserBasedRateLimiter

        rate_limiter = UserBasedRateLimiter()
        rate_stats = await rate_limiter.get_usage_stats(user.id)
    except Exception:
        rate_stats = {}

    return templates.TemplateResponse(
        request,
        "pages/todo_details.html",
        {
            "request": request,
            "current_year": datetime.utcnow().year,
            "todo": todo,
            "steps_data": todo.steps or {},
            "rate_stats": rate_stats,
        },
    )
