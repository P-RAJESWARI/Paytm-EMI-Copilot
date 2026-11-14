"""Tests for the core-level upstream call errors that adapters translate into domain errors."""

from emi_copilot.core.upstream_errors import (
    CircuitOpenError,
    UpstreamCallError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)

DEPENDENCY_NAME = "test-gateway"


def test_upstream_errors_share_base_class_carrying_dependency_name() -> None:
    """Adapters can catch one base class and still know which dependency failed."""
    upstream_errors: list[UpstreamCallError] = [
        UpstreamTimeoutError(DEPENDENCY_NAME, "no answer in time", is_outcome_unknown=True),
        UpstreamUnavailableError(
            DEPENDENCY_NAME, "server error", is_outcome_unknown=False, status_code=503
        ),
        CircuitOpenError(DEPENDENCY_NAME),
    ]
    assert {error.dependency_name for error in upstream_errors} == {DEPENDENCY_NAME}


def test_upstream_error_message_names_dependency_and_detail_only() -> None:
    """The message is the dependency and a payload-free detail, nothing else."""
    error = UpstreamTimeoutError(DEPENDENCY_NAME, "no answer in time", is_outcome_unknown=True)
    assert str(error) == "test-gateway: no answer in time"
    assert error.detail == "no answer in time"


def test_circuit_open_error_always_has_known_outcome() -> None:
    """A rejected call was never sent, so it cannot have taken effect."""
    error = CircuitOpenError(DEPENDENCY_NAME)
    assert error.is_outcome_unknown is False
    assert "circuit breaker is open" in str(error)


def test_upstream_unavailable_error_keeps_status_code() -> None:
    """The adapter can see which 5xx the dependency answered with, without its body."""
    error = UpstreamUnavailableError(
        DEPENDENCY_NAME, "server error", is_outcome_unknown=False, status_code=504
    )
    assert error.status_code == 504
