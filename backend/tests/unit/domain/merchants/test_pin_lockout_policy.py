"""Tests for the PIN lockout policy: 5 wrong PINs lock a shop for 15 minutes."""

from datetime import UTC, datetime, timedelta

import pytest

from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.merchants import (
    UNLOCKED_PIN_ATTEMPT_STATE,
    PinAttemptState,
    PinLockoutPolicy,
)

NOW = datetime(2026, 11, 14, 10, 30, tzinfo=UTC)
FIFTEEN_MINUTES = timedelta(minutes=15)


def record_failures(policy: PinLockoutPolicy, failure_count: int) -> PinAttemptState:
    """Applies the given number of wrong PINs at NOW to a fresh shop."""
    state = UNLOCKED_PIN_ATTEMPT_STATE
    for _ in range(failure_count):
        state = policy.record_failed_attempt(state, NOW)
    return state


@pytest.mark.parametrize("failure_count", [1, 2, 3, 4])
def test_record_failed_attempt_below_the_limit_only_counts(failure_count: int) -> None:
    """Wrong PINs 1 to 4 are counted and the shop stays open."""
    policy = PinLockoutPolicy()
    state = record_failures(policy, failure_count)
    assert state == PinAttemptState(consecutive_failure_count=failure_count, locked_until=None)
    assert policy.find_seconds_until_unlocked(state, NOW) is None


def test_record_failed_attempt_fifth_failure_locks_for_fifteen_minutes() -> None:
    """The 5th wrong PIN in a row locks the shop, and the lock starts the count again."""
    policy = PinLockoutPolicy()
    state = record_failures(policy, 5)
    assert state == PinAttemptState(consecutive_failure_count=0, locked_until=NOW + FIFTEEN_MINUTES)
    assert policy.find_seconds_until_unlocked(state, NOW) == 15 * 60


def test_record_failed_attempt_while_locked_does_not_extend_the_lock() -> None:
    """A sixth wrong PIN during the lock leaves the lock end where it was."""
    policy = PinLockoutPolicy()
    locked_state = record_failures(policy, 5)
    later = NOW + timedelta(minutes=10)
    assert policy.record_failed_attempt(locked_state, later) == locked_state
    assert policy.find_seconds_until_unlocked(locked_state, later) == 5 * 60


def test_find_seconds_until_unlocked_rounds_up_and_ends_exactly_at_the_lock_end() -> None:
    """Part of a second counts as a whole second; at the lock end the shop is open again."""
    policy = PinLockoutPolicy()
    locked_state = record_failures(policy, 5)
    lock_end = NOW + FIFTEEN_MINUTES
    assert policy.find_seconds_until_unlocked(locked_state, lock_end - timedelta(seconds=0.2)) == 1
    assert policy.find_seconds_until_unlocked(locked_state, lock_end) is None


def test_record_failed_attempt_after_the_lock_ends_starts_a_fresh_count() -> None:
    """Once unlocked, the shop again has 5 attempts before the next lock."""
    policy = PinLockoutPolicy()
    locked_state = record_failures(policy, 5)
    after_lock = NOW + FIFTEEN_MINUTES
    assert policy.record_failed_attempt(locked_state, after_lock) == PinAttemptState(
        consecutive_failure_count=1, locked_until=None
    )


def test_record_successful_attempt_resets_every_failure() -> None:
    """A right PIN wipes the count, so failures must be consecutive to lock."""
    assert PinLockoutPolicy().record_successful_attempt() == UNLOCKED_PIN_ATTEMPT_STATE


def test_pin_lockout_policy_with_custom_limits_locks_at_its_own_limit() -> None:
    """The limit and the lock length are policy parameters, held in one place."""
    policy = PinLockoutPolicy(maximum_consecutive_failures=2, lockout_duration=timedelta(minutes=1))
    state = record_failures(policy, 2)
    assert state.locked_until == NOW + timedelta(minutes=1)


@pytest.mark.parametrize(
    ("maximum_consecutive_failures", "lockout_duration"),
    [(0, FIFTEEN_MINUTES), (5, timedelta(0))],
)
def test_pin_lockout_policy_with_unusable_limits_raises(
    maximum_consecutive_failures: int, lockout_duration: timedelta
) -> None:
    """A policy that locks before any attempt, or for no time, is a configuration error."""
    with pytest.raises(ValueError, match="must"):
        PinLockoutPolicy(maximum_consecutive_failures, lockout_duration)


@pytest.mark.parametrize(
    ("failure_count", "locked_until"),
    [
        (-1, None),
        (True, None),
        ("1", None),
        (0, datetime(2026, 11, 14, 10, 30)),  # noqa: DTZ001 - the naive moment is the point
    ],
)
def test_pin_attempt_state_with_invalid_fields_raises(
    failure_count: object, locked_until: datetime | None
) -> None:
    """A negative or non-integer count, or a lock end without a time zone, is refused."""
    with pytest.raises(InvalidMerchantDataError):
        PinAttemptState(consecutive_failure_count=failure_count, locked_until=locked_until)  # type: ignore[arg-type]
