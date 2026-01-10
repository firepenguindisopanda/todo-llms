from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies.database import get_db
from app.infrastructure.database.models.todo_model import Todo as TodoModel
from app.infrastructure.database.models.user_model import User as UserModel
from app.web.helpers import get_csrf_token, get_and_pop_flash, get_user_from_cookie, validate_csrf_token, set_flash

router = APIRouter()

templates = Jinja2Templates(directory="app/web/templates")

@router.get("/", response_class=HTMLResponse)
async def root(request: Request, user: UserModel = Depends(get_user_from_cookie), csrf: str = Depends(get_csrf_token), flash: str = Depends(get_and_pop_flash)):
    """Root page: redirect authenticated users to dashboard; otherwise show login page."""
    if user is not None:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    # show login page for guests
    return templates.TemplateResponse(request, "pages/auth/login.html", {"request": request, "current_year": datetime.utcnow().year})

@router.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "pages/home.html", {"request": request, "current_year": datetime.utcnow().year})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_user_from_cookie), csrf: str = Depends(get_csrf_token), flash: str = Depends(get_and_pop_flash)):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    stmt = select(TodoModel).where(TodoModel.user_id == user.id).order_by(TodoModel.created_at.desc())
    result = await db.execute(stmt)
    todos = result.scalars().all()

    return templates.TemplateResponse(request, "pages/dashboard.html", {"request": request, "current_year": datetime.utcnow().year, "todos": todos})

@router.post("/todos/create")
async def create_todo(request: Request, title: str = Form(...), description: str = Form(None), csrf_token: str = Form(None), db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_user_from_cookie)):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    # CSRF validation
    if not validate_csrf_token(request, csrf_token):
        return templates.TemplateResponse(request, "pages/dashboard.html", {"request": request, "error": "Invalid CSRF token", "title": title, "description": description}, status_code=status.HTTP_400_BAD_REQUEST)

    todo = TodoModel(user_id=user.id, title=title, description=description)
    db.add(todo)
    await db.flush()
    await db.commit()
    await db.refresh(todo)

    # flash & redirect
    set_flash(request, "Todo created successfully.")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_user_from_cookie), csrf: str = Depends(get_csrf_token), flash: str = Depends(get_and_pop_flash)):
    """Admin-only dashboard for system overview."""
    if user is None or user.role != 'admin':
        set_flash(request, "Access denied. Admin privileges required.")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    from sqlalchemy import func
    user_count = await db.scalar(select(func.count(UserModel.id)))
    todo_count = await db.scalar(select(func.count(TodoModel.id)))

    # Latest 5 users
    latest_users = (await db.execute(select(UserModel).order_by(UserModel.created_at.desc()).limit(5))).scalars().all()

    return templates.TemplateResponse(request, "pages/admin_dashboard.html", {
        "request": request, 
        "current_year": datetime.utcnow().year,
        "user_count": user_count,
        "todo_count": todo_count,
        "latest_users": latest_users
    })
