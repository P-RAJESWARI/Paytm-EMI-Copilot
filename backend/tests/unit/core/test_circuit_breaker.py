"""Tests for the circuit breaker: opening, cool-down, the single half-open trial and staleness."""

import logging
import threading
from datetime import UTC, datetime, timedelta

import pytest

from emi_copilot.core.circuit_breaker import CallPermit, CircuitBreaker, CircuitState
from emi_copilot.core.upstream_errors import CircuitOpenError
from tests.fixed_clock import FixedClock

DEPENDENCY_NAME = "test-gateway"
FAILURE_THRESHOLD = 3
OPEN_DURATION = timedelta(seconds=30)
STARTING_MOMENT = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)


def read_state(circuit_breaker: CircuitBreaker) -> CircuitState:
    """Reads the breaker's state through a call, so type checkers do not narrow it across steps."""
    return circuit_breaker.state


@pytest.fixture
def clock() -> FixedClock:
    """A clock that only moves when the test moves it."""
    return FixedClock(STARTING_MOMENT)


@pytest.fixture
def circuit_breaker(clock: FixedClock) -> CircuitBreaker:
    """A breaker that opens after three failures and stays open for thirty seconds."""
    return CircuitBreaker(
        dependency_name=DEPENDENCY_NAME,
        failure_threshold=FAILURE_THRESHOLD,
        open_duration=OPEN_DURATION,
        clock=clock,
    )


def record_failures(circuit_breaker: CircuitBreaker, failure_count: int) -> None:
    """Lets the given number of calls through and records each of them as failed."""
    for _ in range(failure_count):
        circuit_breaker.record_failure(circuit_breaker.acquire_call_permit())


def open_and_cool_down(circuit_breaker: CircuitBreaker, clock: FixedClock) -> None:
    """Opens the breaker with threshold failures and waits out the cool-down, so it half-opens."""
    record_failures(circuit_breaker, FAILURE_THRESHOLD)
    clock.advance(OPEN_DURATION)


def test_circuit_breaker_starts_closed_with_no_failures(circuit_breaker: CircuitBreaker) -> None:
    """A new breaker lets calls through and has counted nothing."""
    assert read_state(circuit_breaker) is CircuitState.CLOSED
    assert circuit_breaker.consecutive_failure_count == 0


def test_circuit_breaker_below_threshold_stays_closed(circuit_breaker: CircuitBreaker) -> None:
    """Fewer consecutive failures than the threshold keep the circuit closed."""
    record_failures(circuit_breaker, FAILURE_THRESHOLD - 1)
    assert read_state(circuit_breaker) is CircuitState.CLOSED
    assert circuit_breaker.consecutive_failure_count == FAILURE_THRESHOLD - 1


def test_circuit_breaker_at_threshold_opens(circuit_breaker: CircuitBreaker) -> None:
    """The threshold-th consecutive failure opens the circuit."""
    record_failures(circuit_breaker, FAILURE_THRESHOLD)
    assert read_state(circuit_breaker) is CircuitState.OPEN


def test_circuit_breaker_success_resets_failure_count(circuit_breaker: CircuitBreaker) -> None:
    """Failures must be consecutive: a success in between starts the count again."""
    record_failures(circuit_breaker, FAILURE_THRESHOLD - 1)
    circuit_breaker.record_success(circuit_breaker.acquire_call_permit())
    record_failures(circuit_breaker, FAILURE_THRESHOLD - 1)
    assert read_state(circuit_breaker) is CircuitState.CLOSED
    assert circuit_breaker.consecutive_failure_count == FAILURE_THRESHOLD - 1


def test_circuit_breaker_open_rejects_calls_with_known_outcome(
    circuit_breaker: CircuitBreaker,
) -> None:
    """An open circuit refuses at once; the error says nothing was sent."""
    record_failures(circuit_breaker, FAILURE_THRESHOLD)
    with pytest.raises(CircuitOpenError) as raised_error:
        circuit_breaker.acquire_call_permit()
    assert raised_error.value.dependency_name == DEPENDENCY_NAME
    assert raised_error.value.is_outcome_unknown is False


def test_circuit_breaker_open_before_cool_down_keeps_rejecting(
    circuit_breaker: CircuitBreaker, clock: FixedClock
) -> None:
    """Just before open_duration has passed the circuit is still open."""
    record_failures(circuit_breaker, FAILURE_THRESHOLD)
    clock.advance(OPEN_DURATION - timedelta(milliseconds=1))
    assert read_state(circuit_breaker) is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        circuit_breaker.acquire_call_permit()


def test_circuit_breaker_after_cool_down_half_opens(
    circuit_breaker: CircuitBreaker, clock: FixedClock
) -> None:
    """Once open_duration has passed on the clock the breaker is ready for a trial."""
    open_and_cool_down(circuit_breaker, clock)
    assert read_state(circuit_breaker) is CircuitState.HALF_OPEN


def test_circuit_breaker_half_open_lets_exactly_one_trial_through(
    circuit_breaker: CircuitBreaker, clock: FixedClock
) -> None:
    """While the trial call is in flight every other caller is rejected."""
    open_and_cool_down(circuit_breaker, clock)
    circuit_breaker.acquire_call_permit()
    with pytest.raises(CircuitOpenError):
        circuit_breaker.acquire_call_permit()
    assert read_state(circuit_breaker) is CircuitState.HALF_OPEN


def test_circuit_breaker_half_open_trial_success_closes(
    circuit_breaker: CircuitBreaker, clock: FixedClock
) -> None:
    """A successful trial closes the circuit, so calls flow and the count is zero."""
    open_and_cool_down(circuit_breaker, clock)
    circuit_breaker.record_success(circuit_breaker.acquire_call_permit())
    assert read_state(circuit_breaker) is CircuitState.CLOSED
    assert circuit_breaker.consecutive_failure_count == 0
    circuit_breaker.acquire_call_permit()
    circuit_breaker.acquire_call_permit()


def test_circuit_breaker_half_open_trial_failure_reopens_for_full_duration(
    circuit_breaker: CircuitBreaker, clock: FixedClock
) -> None:
    """A failed trial re-opens the circuit, which then waits a whole new open_duration."""
    open_and_cool_down(circuit_breaker, clock)
    circuit_breaker.record_failure(circuit_breaker.acquire_call_permit())
    assert read_state(circuit_breaker) is CircuitState.OPEN
    clock.advance(OPEN_DURATION - timedelta(milliseconds=1))
    with pytest.raises(CircuitOpenError):
        circuit_breaker.acquire_call_permit()
    clock.advance(timedelta(milliseconds=1))
    assert read_state(circuit_breaker) is CircuitState.HALF_OPEN


def test_circuit_breaker_late_success_from_before_opening_is_ignored(
    circuit_breaker: CircuitBreaker, clock: FixedClock
) -> None:
    """A slow call admitted while closed cannot close the circuit or end the half-open trial."""
    slow_call_permit = circuit_breaker.acquire_call_permit()
    record_failures(circuit_breaker, FAILURE_THRESHOLD)
    circuit_breaker.record_success(slow_call_permit)
    assert read_state(circuit_breaker) is CircuitState.OPEN
    clock.advance(OPEN_DURATION)
    circuit_breaker.acquire_call_permit()
    circuit_breaker.record_success(slow_call_permit)
    assert read_state(circuit_breaker) is CircuitState.HALF_OPEN
    with pytest.raises(CircuitOpenError):
        circuit_breaker.acquire_call_permit()


def test_circuit_breaker_late_failure_from_before_opening_is_ignored(
    circuit_breaker: CircuitBreaker, clock: FixedClock
) -> None:
    """A slow failure admitted while closed cannot re-open a circuit that a trial just closed."""
    slow_call_permit = circuit_breaker.acquire_call_permit()
    open_and_cool_down(circuit_breaker, clock)
    circuit_breaker.record_success(circuit_breaker.acquire_call_permit())
    circuit_breaker.record_failure(slow_call_permit)
    assert read_state(circuit_breaker) is CircuitState.CLOSED
    assert circuit_breaker.consecutive_failure_count == 0


def test_circuit_breaker_half_open_concurrent_callers_get_one_permit(
    circuit_breaker: CircuitBreaker, clock: FixedClock
) -> None:
    """Many threads racing for the half-open trial: exactly one wins, the rest are rejected."""
    open_and_cool_down(circuit_breaker, clock)
    caller_count = 16
    start_barrier = threading.Barrier(caller_count)
    granted_permits: list[CallPermit] = []
    rejection_count = 0
    results_lock = threading.Lock()

    def race_for_permit() -> None:
        """Waits for every caller, then asks for a permit and notes the result."""
        nonlocal rejection_count
        start_barrier.wait()
        try:
            permit = circuit_breaker.acquire_call_permit()
        except CircuitOpenError:
            with results_lock:
                rejection_count += 1
            return
        with results_lock:
            granted_permits.append(permit)

    callers = [threading.Thread(target=race_for_permit) for _ in range(caller_count)]
    for caller in callers:
        caller.start()
    for caller in callers:
        caller.join()
    assert len(granted_permits) == 1
    assert rejection_count == caller_count - 1


def test_circuit_breaker_logs_each_state_change(
    circuit_breaker: CircuitBreaker, clock: FixedClock, caplog: pytest.LogCaptureFixture
) -> None:
    """Opening, half-opening and closing each log one event naming the dependency."""
    caplog.set_level(logging.WARNING, logger="emi_copilot.core.circuit_breaker")
    open_and_cool_down(circuit_breaker, clock)
    circuit_breaker.record_success(circuit_breaker.acquire_call_permit())
    transitions = [
        (record.__dict__["previous_circuit_state"], record.__dict__["circuit_state"])
        for record in caplog.records
    ]
    assert transitions == [("closed", "open"), ("open", "half_open"), ("half_open", "closed")]
    assert {record.__dict__["dependency_name"] for record in caplog.records} == {DEPENDENCY_NAME}


@pytest.mark.parametrize(
    ("failure_threshold", "open_duration"),
    [(0, OPEN_DURATION), (FAILURE_THRESHOLD, timedelta(0))],
    ids=["threshold-below-one", "zero-open-duration"],
)
def test_circuit_breaker_with_unusable_configuration_raises_value_error(
    clock: FixedClock, failure_threshold: int, open_duration: timedelta
) -> None:
    """A breaker that could never open, or never stay open, is refused at construction."""
    with pytest.raises(ValueError, match="must be"):
        CircuitBreaker(
            dependency_name=DEPENDENCY_NAME,
            failure_threshold=failure_threshold,
            open_duration=open_duration,
            clock=clock,
        )
