from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.application.use_cases.user.register_user import register_user
from app.infrastructure.database.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.api.dependencies.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.security.password_hasher import verify_password
from app.infrastructure.security.jwt_handler import create_access_token
from app.infrastructure.security.refresh_token_service import create_refresh_token
from app.config import settings
from app.infrastructure.database.models.user_model import User as UserModel
from sqlalchemy import select
from app.web.helpers import get_csrf_token, get_and_pop_flash

router = APIRouter(prefix="/auth")

templates = Jinja2Templates(directory="app/web/templates")

@router.get("/login", response_class=HTMLResponse)
async def login(request: Request, csrf: str = Depends(get_csrf_token), flash: str = Depends(get_and_pop_flash)):
    # get_csrf_token ensures CSRF is present; get_and_pop_flash pops any flash into request.state
    return templates.TemplateResponse(request, "pages/auth/login.html", {"request": request})

@router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(None), db: AsyncSession = Depends(get_db)):
    # CSRF validation
    from app.web.helpers import validate_csrf_token

    if not validate_csrf_token(request, csrf_token):
        return templates.TemplateResponse(request, "pages/auth/login.html", {"request": request, "error": "Invalid CSRF token", "email": email}, status_code=status.HTTP_400_BAD_REQUEST)

    # Authenticate user using same logic as API /api/v1/auth/login
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user_model = result.scalar_one_or_none()
    if user_model is None or not verify_password(password, user_model.password_hash):
        # on failure re-render login with error and preserve email
        return templates.TemplateResponse(request, "pages/auth/login.html", {"request": request, "error": "Invalid credentials", "email": email}, status_code=status.HTTP_401_UNAUTHORIZED)

    # successful login: create tokens and set refresh cookie
    access_token = create_access_token(subject=str(user_model.id))
    refresh_token = await create_refresh_token(db, user_model.id)

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=not settings.DEBUG, samesite="lax", max_age=max_age)
    return response

@router.get("/register", response_class=HTMLResponse)
async def register(request: Request, csrf: str = Depends(get_csrf_token), flash: str = Depends(get_and_pop_flash)):
    # get_csrf_token ensures CSRF is present; get_and_pop_flash pops any flash into request.state
    return templates.TemplateResponse(request, "pages/auth/register.html", {"request": request})

@router.post("/register")
async def register_post(request: Request, email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), csrf_token: str = Form(None), db: AsyncSession = Depends(get_db)):
    # CSRF validation
    from app.web.helpers import validate_csrf_token

    if not validate_csrf_token(request, csrf_token):
        return templates.TemplateResponse(request, "pages/auth/register.html", {"request": request, "error": "Invalid CSRF token", "email": email}, status_code=status.HTTP_400_BAD_REQUEST)

    if password != confirm_password:
        return templates.TemplateResponse(request, "pages/auth/register.html", {"request": request, "error": "Passwords do not match", "email": email}, status_code=status.HTTP_400_BAD_REQUEST)

    repo = SQLAlchemyUserRepository(db)
    try:
        await register_user(email, password, repo)
    except ValueError as e:
        return templates.TemplateResponse(request, "pages/auth/register.html", {"request": request, "error": str(e), "email": email}, status_code=status.HTTP_400_BAD_REQUEST)

    # on success set flash in session and redirect to login (use helper)
    from app.web.helpers import set_flash

    set_flash(request, "Registration successful. Please log in.")
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form(None)):
    """Log out a user by clearing the refresh_token cookie."""
    # Optional: validate CSRF if you want to prevent logout CSRF
    from app.web.helpers import validate_csrf_token
    if not validate_csrf_token(request, csrf_token):
        # Even if CSRF fails, we can just log out for safety, or return error.
        # But for logout, failing CSRF might just mean we stay logged in.
        # Let's be strict for consistency.
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("refresh_token")
    
    from app.web.helpers import set_flash
    set_flash(request, "Logged out successfully.")
    
    return response
