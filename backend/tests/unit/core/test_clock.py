"""Tests for the injectable clock."""

from datetime import UTC, datetime

from emi_copilot.core.clock import Clock, SystemClock


def test_system_clock_now_returns_timezone_aware_utc_datetime() -> None:
    """Domain timestamps are always UTC and never naive."""
    current_moment = SystemClock().now()
    assert current_moment.tzinfo is UTC


def test_system_clock_now_returns_the_current_moment() -> None:
    """The system clock reads the real wall clock."""
    clock: Clock = SystemClock()
    moment_before = datetime.now(UTC)
    current_moment = clock.now()
    moment_after = datetime.now(UTC)
    assert moment_before <= current_moment <= moment_after
