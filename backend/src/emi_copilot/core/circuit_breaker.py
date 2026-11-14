"""Circuit breaker that stops calling a dependency after repeated failures, then probes it."""

import logging
import threading
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from emi_copilot.core.clock import Clock
from emi_copilot.core.upstream_errors import CircuitOpenError

circuit_breaker_logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    """Where a circuit breaker stands: passing calls, rejecting them, or probing with one."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CallPermit:
    """Proof that the breaker let one call through; its outcome must be recorded with it.

    open_count is how many times the circuit had opened when the call was let through. An outcome
    whose permit is older than the latest opening is stale and does not change the state.
    """

    open_count: int


# Pattern: Circuit Breaker. A dependency that keeps failing is rejected immediately for a
# cool-down instead of tying up callers on timeouts; one trial call then decides whether to close.
class CircuitBreaker:
    """Thread-safe breaker for one dependency, timed by an injected Clock.

    CLOSED opens after failure_threshold consecutive failures. OPEN rejects every call until
    open_duration has passed, then turns HALF_OPEN, which lets exactly one trial call through and
    rejects the rest while it is in flight. The trial's success closes the circuit and resets the
    count; its failure opens the circuit again for another open_duration.
    """

    def __init__(
        self,
        *,
        dependency_name: str,
        failure_threshold: int,
        open_duration: timedelta,
        clock: Clock,
    ) -> None:
        """Starts CLOSED with no failures; refuses a threshold below 1 or a duration of zero."""
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if open_duration <= timedelta(0):
            raise ValueError("open_duration must be positive")
        self.dependency_name = dependency_name
        self._failure_threshold = failure_threshold
        self._open_duration = open_duration
        self._clock = clock
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._consecutive_failure_count = 0
        self._open_count = 0
        self._opened_at = clock.now()
        self._is_trial_call_in_flight = False

    @property
    def state(self) -> CircuitState:
        """Gives the current state, turning OPEN into HALF_OPEN once the cool-down has passed."""
        with self._lock:
            self._half_open_if_cool_down_passed()
            return self._state

    @property
    def consecutive_failure_count(self) -> int:
        """Gives how many failures in a row were recorded since the last success or opening."""
        with self._lock:
            return self._consecutive_failure_count

    def acquire_call_permit(self) -> CallPermit:
        """Lets a call through and returns its permit, or raises CircuitOpenError without one."""
        with self._lock:
            self._half_open_if_cool_down_passed()
            if self._state is CircuitState.OPEN or self._is_trial_call_in_flight:
                raise CircuitOpenError(self.dependency_name)
            if self._state is CircuitState.HALF_OPEN:
                self._is_trial_call_in_flight = True
            return CallPermit(open_count=self._open_count)

    def record_success(self, permit: CallPermit) -> None:
        """Counts a healthy answer: resets the failure count and closes a HALF_OPEN circuit."""
        with self._lock:
            if self._is_stale(permit):
                return
            self._consecutive_failure_count = 0
            if self._state is CircuitState.HALF_OPEN:
                self._is_trial_call_in_flight = False
                self._change_state(CircuitState.CLOSED)

    def record_failure(self, permit: CallPermit) -> None:
        """Counts a failure: opens after the threshold in CLOSED, or re-opens from HALF_OPEN."""
        with self._lock:
            if self._is_stale(permit):
                return
            self._consecutive_failure_count += 1
            if (
                self._state is CircuitState.HALF_OPEN
                or self._consecutive_failure_count >= self._failure_threshold
            ):
                self._open()

    def _is_stale(self, permit: CallPermit) -> bool:
        """Tells whether the permit predates the latest opening, so its outcome is ignored."""
        return permit.open_count != self._open_count

    def _open(self) -> None:
        """Opens the circuit now; outstanding permits become stale and the failure count resets."""
        self._open_count += 1
        self._opened_at = self._clock.now()
        self._consecutive_failure_count = 0
        self._is_trial_call_in_flight = False
        self._change_state(CircuitState.OPEN)

    def _half_open_if_cool_down_passed(self) -> None:
        """Moves an OPEN circuit to HALF_OPEN once open_duration has passed on the clock."""
        is_cool_down_over = self._clock.now() - self._opened_at >= self._open_duration
        if self._state is CircuitState.OPEN and is_cool_down_over:
            self._change_state(CircuitState.HALF_OPEN)

    def _change_state(self, new_state: CircuitState) -> None:
        """Sets the state and logs one structured event for the transition."""
        previous_state = self._state
        self._state = new_state
        circuit_breaker_logger.warning(
            "circuit breaker state changed",
            extra={
                "dependency_name": self.dependency_name,
                "previous_circuit_state": previous_state.value,
                "circuit_state": new_state.value,
            },
        )
