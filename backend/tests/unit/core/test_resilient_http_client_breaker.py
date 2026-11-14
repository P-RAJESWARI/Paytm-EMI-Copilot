"""Resilient HTTP client behind its circuit breaker, and the safety of its log events."""

import json
import logging

import httpx
import pytest

from emi_copilot.core.circuit_breaker import CircuitState
from emi_copilot.core.logging import JsonLogFormatter
from emi_copilot.core.upstream_errors import (
    CircuitOpenError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from tests.unit.core.resilient_client_harness import (
    CLIENT_LOGGER_NAME,
    DEPENDENCY_NAME,
    OPEN_DURATION,
    SYNTHETIC_QUERY_VALUE,
    ClientFactory,
    build_request,
    read_state,
)

# Circuit breaker behind the client


def test_resilient_client_opens_breaker_after_threshold_and_stops_calling_transport(
    build_client_under_test: ClientFactory,
) -> None:
    """After the configured consecutive failures the gateway is not called at all."""
    under_test = build_client_under_test([503], failure_threshold=3)
    for _ in range(3):
        with pytest.raises(UpstreamUnavailableError):
            under_test.client.send_non_idempotent(build_request())
    assert read_state(under_test.circuit_breaker) is CircuitState.OPEN
    with pytest.raises(CircuitOpenError) as raised_error:
        under_test.client.send_non_idempotent(build_request())
    with pytest.raises(CircuitOpenError):
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 3
    assert raised_error.value.is_outcome_unknown is False


def test_send_idempotent_stops_retrying_when_breaker_opens(
    build_client_under_test: ClientFactory,
) -> None:
    """Retries count on the breaker; once it opens the remaining attempts are not sent."""
    under_test = build_client_under_test([httpx.ReadTimeout], max_attempts=5, failure_threshold=2)
    with pytest.raises(CircuitOpenError):
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 2


def test_resilient_client_client_errors_do_not_count_as_breaker_failures(
    build_client_under_test: ClientFactory,
) -> None:
    """Many 4xx answers in a row never open the circuit: the gateway is answering."""
    under_test = build_client_under_test([400], failure_threshold=2)
    for _ in range(5):
        under_test.client.send_non_idempotent(build_request())
    assert read_state(under_test.circuit_breaker) is CircuitState.CLOSED
    assert under_test.circuit_breaker.consecutive_failure_count == 0


def test_resilient_client_success_resets_breaker_failure_count(
    build_client_under_test: ClientFactory,
) -> None:
    """Failures separated by a success do not add up to an opening."""
    under_test = build_client_under_test([503, 200, 503], failure_threshold=2)
    with pytest.raises(UpstreamUnavailableError):
        under_test.client.send_non_idempotent(build_request())
    under_test.client.send_non_idempotent(build_request())
    with pytest.raises(UpstreamUnavailableError):
        under_test.client.send_non_idempotent(build_request())
    assert read_state(under_test.circuit_breaker) is CircuitState.CLOSED
    assert under_test.circuit_breaker.consecutive_failure_count == 1


def test_resilient_client_after_cool_down_trial_success_closes_breaker(
    build_client_under_test: ClientFactory,
) -> None:
    """After open_duration one trial call reaches the gateway; its success closes the circuit."""
    under_test = build_client_under_test([503, 200], failure_threshold=1)
    with pytest.raises(UpstreamUnavailableError):
        under_test.client.send_non_idempotent(build_request())
    under_test.clock.advance(OPEN_DURATION)
    assert read_state(under_test.circuit_breaker) is CircuitState.HALF_OPEN
    assert under_test.client.send_non_idempotent(build_request()).status_code == 200
    assert read_state(under_test.circuit_breaker) is CircuitState.CLOSED
    assert under_test.transport_call_count == 2


def test_resilient_client_after_cool_down_trial_failure_reopens_breaker(
    build_client_under_test: ClientFactory,
) -> None:
    """A failed trial re-opens the circuit, so the next call is rejected without being sent."""
    under_test = build_client_under_test([503], failure_threshold=1)
    with pytest.raises(UpstreamUnavailableError):
        under_test.client.send_non_idempotent(build_request())
    under_test.clock.advance(OPEN_DURATION)
    with pytest.raises(UpstreamUnavailableError):
        under_test.client.send_non_idempotent(build_request())
    assert read_state(under_test.circuit_breaker) is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 2


# Logs


def render_client_log_lines(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    """Formats every captured client log record as the production JSON line, parsed back."""
    formatter = JsonLogFormatter()
    return [
        json.loads(formatter.format(record))
        for record in caplog.records
        if record.name == CLIENT_LOGGER_NAME
    ]


def test_send_idempotent_retry_log_has_host_and_path_but_not_query_string(
    build_client_under_test: ClientFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """Retry and failure events name host and path only; the query may carry a merchant id."""
    caplog.set_level(logging.WARNING, logger=CLIENT_LOGGER_NAME)
    under_test = build_client_under_test([httpx.ReadTimeout], max_attempts=2)
    with pytest.raises(UpstreamTimeoutError):
        under_test.client.send_idempotent(build_request())
    retry_line, failure_line = render_client_log_lines(caplog)
    assert retry_line["message"] == "upstream call retry scheduled"
    assert retry_line["upstream_host"] == "gateway.example.test"
    assert retry_line["upstream_path"] == "/v1/order/status"
    assert retry_line["attempt_number"] == 1
    assert retry_line["failure_reason"] == "ReadTimeout"
    assert retry_line["dependency_name"] == DEPENDENCY_NAME
    assert retry_line["http_method"] == "POST"
    assert retry_line["retry_delay_in_seconds"] == under_test.recorded_sleep_delays[0]
    assert failure_line["message"] == "upstream call failed"
    assert failure_line["attempt_number"] == 2
    assert SYNTHETIC_QUERY_VALUE not in caplog.text
    for log_line in (retry_line, failure_line):
        assert SYNTHETIC_QUERY_VALUE not in json.dumps(log_line)
        assert "ORDER-0001" not in json.dumps(log_line)


def test_send_non_idempotent_failure_log_names_reason_and_outcome(
    build_client_under_test: ClientFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed create call logs one event with its status and whether the outcome is unknown."""
    caplog.set_level(logging.WARNING, logger=CLIENT_LOGGER_NAME)
    under_test = build_client_under_test([503])
    with pytest.raises(UpstreamUnavailableError):
        under_test.client.send_non_idempotent(build_request())
    (failure_line,) = render_client_log_lines(caplog)
    assert failure_line["failure_reason"] == "http_status_503"
    assert failure_line["http_status_code"] == 503
    assert failure_line["is_outcome_unknown"] is False
    assert failure_line["attempt_number"] == 1
