"""Per-request correlation ID: accepted from the caller or generated, stored and echoed."""

import logging
import re
import time
from contextvars import ContextVar

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from emi_copilot.core.id_generator import IdGenerator

CORRELATION_ID_HEADER_NAME = "X-Correlation-Id"

# ULIDs (26) and UUIDs (36) fit; anything else odd is replaced so it cannot pollute logs.
VALID_CORRELATION_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{8,64}")

correlation_id_context: ContextVar[str | None] = ContextVar("correlation_id", default=None)

request_logger = logging.getLogger("emi_copilot.request")


def get_current_correlation_id() -> str | None:
    """Returns the correlation ID of the request being handled, or None outside a request."""
    return correlation_id_context.get()


def is_valid_correlation_id(candidate_correlation_id: str) -> bool:
    """Tells whether a caller-supplied correlation ID has a safe format and length."""
    return VALID_CORRELATION_ID_PATTERN.fullmatch(candidate_correlation_id) is not None


def log_completed_request(scope: Scope, response_status_code: int, started_at: float) -> None:
    """Logs one event per request with method, path, status and duration, never the payload."""
    request_logger.info(
        "request completed",
        extra={
            "http_method": scope["method"],
            "http_path": scope["path"],
            "http_status_code": response_status_code,
            "duration_in_milliseconds": round((time.perf_counter() - started_at) * 1000),
        },
    )


class CorrelationIdMiddleware:
    """ASGI middleware that binds one correlation ID to every request, log line and response."""

    def __init__(self, application: ASGIApp, id_generator: IdGenerator) -> None:
        """Wraps the next ASGI application and keeps the generator used for missing IDs."""
        self._application = application
        self._id_generator = id_generator

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Sets the correlation ID for an HTTP request, echoes it and logs the completed request."""
        if scope["type"] != "http":
            await self._application(scope, receive, send)
            return
        correlation_id, was_supplied_value_replaced = self._resolve_correlation_id(scope)
        context_token = correlation_id_context.set(correlation_id)
        if was_supplied_value_replaced:
            request_logger.warning("invalid correlation id header replaced")
        response_status_code = 0
        started_at = time.perf_counter()

        async def send_with_correlation_id(message: Message) -> None:
            """Adds the correlation ID header to the response start message."""
            nonlocal response_status_code
            if message["type"] == "http.response.start":
                response_status_code = message["status"]
                MutableHeaders(scope=message)[CORRELATION_ID_HEADER_NAME] = correlation_id
            await send(message)

        try:
            await self._application(scope, receive, send_with_correlation_id)
        finally:
            log_completed_request(scope, response_status_code, started_at)
            correlation_id_context.reset(context_token)

    def _resolve_correlation_id(self, scope: Scope) -> tuple[str, bool]:
        """Returns the caller's ID if valid, else a new one, and whether a bad one was replaced."""
        supplied_correlation_id = Headers(scope=scope).get(CORRELATION_ID_HEADER_NAME)
        if supplied_correlation_id is not None and is_valid_correlation_id(supplied_correlation_id):
            return supplied_correlation_id, False
        return self._id_generator.new_id(), supplied_correlation_id is not None
