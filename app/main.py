from fastapi import FastAPI, HTTPException
from app.config import settings

from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import configure_logging, logger

# Try to attach SlowAPI middleware if available; it's optional for local dev/test
try:
    from slowapi.middleware import SlowAPIMiddleware  # type: ignore
    from app.rate_limiter import limiter  # type: ignore
    HAS_SLOWAPI = True
except Exception:
    SlowAPIMiddleware = None
    limiter = None
    HAS_SLOWAPI = False


# Configure logging
configure_logging()
from starlette.middleware.base import BaseHTTPMiddleware
import logging

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger.info(f"{request.method} {request.url.path}")
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(f"Error handling {request.method} {request.url.path}: {exc}")
            raise
        return response


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
# Add logging middleware after app is defined
app.add_middleware(RequestLoggingMiddleware)

# Templates & static (for server-rendered pages)
from fastapi.templating import Jinja2Templates
from fastapi import Request
from starlette.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime

templates = Jinja2Templates(directory="app/web/templates")
# Provide a safe STATIC_URL global to templates so templates can use it
templates.env.globals["STATIC_URL"] = "/static/"
# Session middleware for flash messages and CSRF token storage
# Use SESSION_SECRET_KEY if set, otherwise fall back to JWT_SECRET_KEY
session_secret = getattr(settings, "SESSION_SECRET_KEY", None) or settings.JWT_SECRET_KEY
app.add_middleware(SessionMiddleware, secret_key=session_secret)

# Use a class-based TemplateContextMiddleware (added after SessionMiddleware)
from app.web.middleware import TemplateContextMiddleware
app.add_middleware(TemplateContextMiddleware)

# Also import ensure_csrf_token (used as dependency in routes that render forms)
from app.web.helpers import ensure_csrf_token

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Attach rate limiter (memory storage) if available
if HAS_SLOWAPI and SlowAPIMiddleware is not None and limiter is not None:
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

# CORS (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root is handled by web routes (server-rendered pages). See app/web/routes/pages.py for the
# behaviour of the root '/' route which will render the login page for guests or redirect
# authenticated users to the dashboard.

# include api routers
from app.api.v1.router import router as api_v1_router
app.include_router(api_v1_router, prefix="/api/v1")

# include web (HTML) routes
from app.web.routes.pages import router as pages_router
from app.web.routes.auth import router as web_auth_router
from app.web.routes.cookies import router as cookies_router
app.include_router(pages_router)
app.include_router(web_auth_router)
app.include_router(cookies_router)

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    raise HTTPException(status_code=404, detail="Not Found - legacy endpoint removed")