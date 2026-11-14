"""PIN lockout: after repeated wrong pairing PINs a shop refuses every PIN for a while."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.payments.field_validation import require_timezone_aware_moment

DEFAULT_MAXIMUM_CONSECUTIVE_FAILURES = 5
DEFAULT_LOCKOUT_DURATION = timedelta(minutes=15)


# Pattern: Value Object. A shop's PIN attempt record; the policy returns a new one per attempt.
@dataclass(frozen=True, slots=True)
class PinAttemptState:
    """How many wrong PINs in a row a shop has seen, and until when it is locked, if it is."""

    consecutive_failure_count: int
    locked_until: datetime | None

    def __post_init__(self) -> None:
        """Rejects a negative or non-integer count and a lock end without a time zone."""
        if (
            isinstance(self.consecutive_failure_count, bool)
            or not isinstance(self.consecutive_failure_count, int)
            or self.consecutive_failure_count < 0
        ):
            raise InvalidMerchantDataError("The failure count must be a whole number, 0 or more.")
        if self.locked_until is not None:
            require_timezone_aware_moment(self.locked_until, "lock end", InvalidMerchantDataError)


UNLOCKED_PIN_ATTEMPT_STATE = PinAttemptState(consecutive_failure_count=0, locked_until=None)
"""A shop with no wrong PIN since its last success, and no lock."""


class PinLockoutPolicy:
    """Locks a shop for a fixed time after N wrong PINs in a row; a right PIN resets the count.

    With the defaults, wrong PINs 1 to 4 are only counted, the 5th locks the shop for 15
    minutes, and while it is locked even the right PIN is refused. The lock sets the count back
    to zero, so after it ends the shop has N fresh attempts. These are demo values held in one
    place; production values need a security review.
    """

    def __init__(
        self,
        maximum_consecutive_failures: int = DEFAULT_MAXIMUM_CONSECUTIVE_FAILURES,
        lockout_duration: timedelta = DEFAULT_LOCKOUT_DURATION,
    ) -> None:
        """Keeps the failure limit and the lock length; both must be positive."""
        if maximum_consecutive_failures < 1:
            raise ValueError("At least one failure must be allowed before a lock.")
        if lockout_duration <= timedelta(0):
            raise ValueError("The lockout duration must be positive.")
        self._maximum_consecutive_failures = maximum_consecutive_failures
        self._lockout_duration = lockout_duration

    def find_seconds_until_unlocked(self, state: PinAttemptState, now: datetime) -> int | None:
        """Gives the whole seconds, at least one, until the lock ends, or None when unlocked."""
        if state.locked_until is None or now >= state.locked_until:
            return None
        return max(1, math.ceil((state.locked_until - now).total_seconds()))

    def record_failed_attempt(self, state: PinAttemptState, now: datetime) -> PinAttemptState:
        """Counts one wrong PIN, locking the shop when the limit is reached.

        A failure while the shop is already locked changes nothing, so it cannot stretch the lock.
        """
        if self.find_seconds_until_unlocked(state, now) is not None:
            return state
        failure_count = state.consecutive_failure_count + 1
        if failure_count >= self._maximum_consecutive_failures:
            return PinAttemptState(
                consecutive_failure_count=0, locked_until=now + self._lockout_duration
            )
        return PinAttemptState(consecutive_failure_count=failure_count, locked_until=None)

    def record_successful_attempt(self) -> PinAttemptState:
        """Gives the state after a right PIN: no failures counted and no lock."""
        return UNLOCKED_PIN_ATTEMPT_STATE
