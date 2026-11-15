"""The pairing rate-limit dependency keys clients by peer address and refuses over the limit."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from starlette.requests import Request

from emi_copilot.api.rate_limiting import (
    UNKNOWN_CLIENT_ADDRESS,
    enforce_consent_otp_request_rate_limit,
    enforce_customer_consent_rate_limit,
    enforce_customer_session_start_rate_limit,
    enforce_pairing_rate_limit,
    find_client_address,
    find_client_and_customer_session_key,
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


def build_customer_request(client: tuple[str, int], customer_session_id: str) -> Request:
    """Builds a bare customer request from a peer for one session id in the path."""
    return Request(
        {
            "type": "http",
            "method": "POST",
            "headers": [],
            "client": client,
            "path_params": {"customerSessionId": customer_session_id},
        }
    )


def test_customer_key_joins_the_peer_address_and_the_session_id() -> None:
    """A code or consent allowance belongs to one phone on one session."""
    request = build_customer_request(("203.0.113.7", 50000), "01JCSESSION")
    assert find_client_and_customer_session_key(request) == "203.0.113.7 01JCSESSION"


def test_customer_session_start_limit_counts_per_client_address() -> None:
    """The QR exchange is counted before the token is read, per peer address."""
    clock = FixedClock(datetime(2026, 11, 15, 9, 30, 0, tzinfo=UTC))
    limiter = FixedWindowRateLimiter(clock, 1, timedelta(minutes=1))
    enforce_customer_session_start_rate_limit(build_request(("203.0.113.7", 1)), limiter)
    enforce_customer_session_start_rate_limit(build_request(("203.0.113.8", 1)), limiter)
    with pytest.raises(RequestRateLimitedError, match="QR exchanges") as raised:
        enforce_customer_session_start_rate_limit(build_request(("203.0.113.7", 2)), limiter)
    assert raised.value.retry_after_in_seconds == 60


@pytest.mark.parametrize(
    ("enforce_limit", "expected_detail"),
    [
        (enforce_consent_otp_request_rate_limit, "one-time code requests"),
        (enforce_customer_consent_rate_limit, "consent attempts"),
    ],
)
def test_customer_code_and_consent_limits_count_per_address_and_session(
    enforce_limit: Callable[[Request, FixedWindowRateLimiter], None], expected_detail: str
) -> None:
    """Another session from the same phone, or the same session elsewhere, has its own count."""
    clock = FixedClock(datetime(2026, 11, 15, 9, 30, 0, tzinfo=UTC))
    limiter = FixedWindowRateLimiter(clock, 1, timedelta(minutes=10))
    enforce_limit(build_customer_request(("203.0.113.7", 1), "session-a"), limiter)
    enforce_limit(build_customer_request(("203.0.113.7", 1), "session-b"), limiter)
    enforce_limit(build_customer_request(("203.0.113.8", 1), "session-a"), limiter)
    with pytest.raises(RequestRateLimitedError, match=expected_detail):
        enforce_limit(build_customer_request(("203.0.113.7", 2), "session-a"), limiter)
