"""The pairing rate-limit dependency keys clients by peer address and refuses over the limit."""

from datetime import UTC, datetime, timedelta

import pytest
from starlette.requests import Request

from emi_copilot.api.rate_limiting import (
    UNKNOWN_CLIENT_ADDRESS,
    enforce_pairing_rate_limit,
    find_client_address,
)
from emi_copilot.core.fixed_window_rate_limiter import FixedWindowRateLimiter
from emi_copilot.domain.errors import RequestRateLimitedError
from tests.fixed_clock import FixedClock


def build_request(client: tuple[str, int] | None, forwarded_for: str | None = None) -> Request:
    """Builds a bare HTTP request from the given peer, optionally with X-Forwarded-For."""
    headers = [] if forwarded_for is None else [(b"x-forwarded-for", forwarded_for.encode())]
    return Request({"type": "http", "method": "POST", "headers": headers, "client": client})


def test_find_client_address_uses_the_peer_and_ignores_forwarded_for() -> None:
    """A client cannot dodge the limit by sending its own X-Forwarded-For."""
    request = build_request(("203.0.113.7", 50000), forwarded_for="198.51.100.1")
    assert find_client_address(request) == "203.0.113.7"


def test_find_client_address_without_a_peer_uses_one_shared_key() -> None:
    """Requests with no known peer share one allowance rather than escaping the limit."""
    assert find_client_address(build_request(None)) == UNKNOWN_CLIENT_ADDRESS


def test_enforce_pairing_rate_limit_over_the_limit_raises_with_retry_after() -> None:
    """The first request passes; the second in the window is refused with the seconds left."""
    clock = FixedClock(datetime(2026, 11, 14, 10, 30, 20, tzinfo=UTC))
    limiter = FixedWindowRateLimiter(clock, 1, timedelta(minutes=1))
    request = build_request(("203.0.113.7", 50000))
    enforce_pairing_rate_limit(request, limiter)
    with pytest.raises(RequestRateLimitedError) as raised:
        enforce_pairing_rate_limit(request, limiter)
    assert raised.value.retry_after_in_seconds == 40
