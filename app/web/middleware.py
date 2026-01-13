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
                flash_data = pop_flash(request)
                if flash_data:
                    message = flash_data.get("message")
                    category = flash_data.get("category", "success")
                    logger.info("dispatch: popped flash=%s category=%s", message, category)
                    request.state.flash = message
                    request.state.flash_category = category
                else:
                    request.state.flash = None
                    request.state.flash_category = None
            else:
                logger.debug("dispatch: no session in scope, skipping pop_flash")
                request.state.flash = None
                request.state.flash_category = None
        except Exception:
            request.state.flash = None
            request.state.flash_category = None

        response = await call_next(request)
        return response
