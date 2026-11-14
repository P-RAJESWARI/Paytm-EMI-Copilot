"""Tests for the in-memory fixed-window rate limiter driven by a fake clock."""

from datetime import UTC, datetime, timedelta

import pytest

from emi_copilot.core.fixed_window_rate_limiter import FixedWindowRateLimiter, RateLimitDecision
from tests.fixed_clock import FixedClock

# 10:30:15 UTC: fifteen seconds into a one-minute window aligned to the epoch.
START_OF_TEST = datetime(2026, 11, 14, 10, 30, 15, tzinfo=UTC)
ONE_MINUTE = timedelta(minutes=1)
CLIENT_ADDRESS = "client-a"


def build_limiter(clock: FixedClock, maximum_requests: int = 3) -> FixedWindowRateLimiter:
    """Builds a limiter allowing the given number of requests a minute."""
    return FixedWindowRateLimiter(clock, maximum_requests, ONE_MINUTE)


def test_try_acquire_under_the_limit_allows_every_request() -> None:
    """The first N requests in a window go ahead."""
    limiter = build_limiter(FixedClock(START_OF_TEST))
    decisions = [limiter.try_acquire(CLIENT_ADDRESS) for _ in range(3)]
    assert decisions == [RateLimitDecision(is_allowed=True, retry_after_in_seconds=0)] * 3


def test_try_acquire_over_the_limit_refuses_until_the_window_ends() -> None:
    """Request N + 1 is refused and told how long until the window ends (45 s here)."""
    limiter = build_limiter(FixedClock(START_OF_TEST))
    for _ in range(3):
        limiter.try_acquire(CLIENT_ADDRESS)
    assert limiter.try_acquire(CLIENT_ADDRESS) == RateLimitDecision(
        is_allowed=False, retry_after_in_seconds=45
    )


def test_try_acquire_refusal_does_not_count_against_the_next_window() -> None:
    """Refused requests are not counted, and a new window starts with a clean count."""
    clock = FixedClock(START_OF_TEST)
    limiter = build_limiter(clock)
    for _ in range(5):
        limiter.try_acquire(CLIENT_ADDRESS)
    clock.advance(timedelta(seconds=45))
    assert [limiter.try_acquire(CLIENT_ADDRESS).is_allowed for _ in range(4)] == [
        True,
        True,
        True,
        False,
    ]


def test_try_acquire_one_second_before_window_end_still_refuses_with_one_second() -> None:
    """Retry-After is rounded up and never zero while the request is refused."""
    clock = FixedClock(START_OF_TEST)
    limiter = build_limiter(clock, maximum_requests=1)
    limiter.try_acquire(CLIENT_ADDRESS)
    clock.advance(timedelta(seconds=44, milliseconds=500))
    assert limiter.try_acquire(CLIENT_ADDRESS) == RateLimitDecision(
        is_allowed=False, retry_after_in_seconds=1
    )


def test_try_acquire_counts_each_key_separately() -> None:
    """One noisy client does not use up another client's allowance."""
    limiter = build_limiter(FixedClock(START_OF_TEST), maximum_requests=1)
    assert limiter.try_acquire("client-a").is_allowed is True
    assert limiter.try_acquire("client-a").is_allowed is False
    assert limiter.try_acquire("client-b").is_allowed is True


def test_try_acquire_when_tracking_is_full_forgets_only_finished_windows() -> None:
    """Old keys are dropped once the table is full; keys of the current window are kept."""
    clock = FixedClock(START_OF_TEST)
    limiter = FixedWindowRateLimiter(clock, 1, ONE_MINUTE, maximum_tracked_key_count=2)
    limiter.try_acquire("old-client")
    clock.advance(ONE_MINUTE)
    limiter.try_acquire("current-client")
    assert limiter.tracked_key_count == 2
    limiter.try_acquire("third-client")
    assert limiter.tracked_key_count == 2
    assert limiter.try_acquire("current-client").is_allowed is False
    assert limiter.try_acquire("third-client").is_allowed is False


@pytest.mark.parametrize(
    ("maximum_requests", "window_duration"),
    [(0, ONE_MINUTE), (1, timedelta(0)), (1, timedelta(seconds=-1))],
)
def test_fixed_window_rate_limiter_with_unusable_limits_raises(
    maximum_requests: int, window_duration: timedelta
) -> None:
    """A limiter that could never allow a request, or has no window, is a configuration error."""
    with pytest.raises(ValueError, match="must"):
        FixedWindowRateLimiter(FixedClock(START_OF_TEST), maximum_requests, window_duration)
