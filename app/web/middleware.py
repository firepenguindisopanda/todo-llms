from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from typing import Callable
from starlette.responses import Response

from app.web.helpers import pop_flash


class TemplateContextMiddleware(BaseHTTPMiddleware):
    """Middleware to inject flash into request.state for templates.

    This middleware intentionally *does not* call ensure_csrf_token because CSRF
    is established by the `get_csrf_token` dependency on GET routes that render
    forms. That ensures the session cookie is created and persisted properly.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        try:
            import logging
            logger = logging.getLogger("app.web.middleware")
            # Only attempt to access session if it's been installed
            if "session" in request.scope:
                flash = pop_flash(request)
                logger.info("dispatch: popped flash=%s session_keys=%s", flash, list(request.session.keys()))
                request.state.flash = flash
            else:
                logger.debug("dispatch: no session in scope, skipping pop_flash")
                request.state.flash = None
        except Exception:
            request.state.flash = None

        response = await call_next(request)
        return response
