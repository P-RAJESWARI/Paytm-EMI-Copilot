"""Turns any unexpected exception into a generic 500 problem that keeps the correlation id.

Starlette sends a handler for Exception from ServerErrorMiddleware, which sits outside every
user middleware, so its response would miss X-Correlation-Id and the log line its id. This
middleware runs inside CorrelationIdMiddleware instead, so both stay intact.
"""

import logging

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from emi_copilot.api.error_handlers import (
    UNEXPECTED_ERROR_CODE,
    build_problem,
    build_problem_response,
)

unexpected_error_logger = logging.getLogger(__name__)


class UnexpectedErrorMiddleware:
    """ASGI middleware that answers an unhandled exception with a 500 problem, no stack trace."""

    def __init__(self, application: ASGIApp) -> None:
        """Wraps the next ASGI application."""
        self._application = application

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Passes the request on; if it fails before responding, logs it and sends a 500 problem."""
        if scope["type"] != "http":
            await self._application(scope, receive, send)
            return
        has_response_started = False

        async def send_and_track(message: Message) -> None:
            """Remembers whether the response has started, so a late failure is not masked."""
            nonlocal has_response_started
            if message["type"] == "http.response.start":
                has_response_started = True
            await send(message)

        try:
            await self._application(scope, receive, send_and_track)
        except Exception:
            unexpected_error_logger.exception("unexpected error while handling a request")
            if has_response_started:
                raise
            problem = build_problem(
                500,
                UNEXPECTED_ERROR_CODE,
                "Internal server error",
                "An unexpected error occurred; quote the correlation id when reporting it.",
            )
            await build_problem_response(problem)(scope, receive, send)
