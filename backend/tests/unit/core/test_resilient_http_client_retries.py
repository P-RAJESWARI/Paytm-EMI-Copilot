"""Resilient HTTP client: idempotent calls are retried with jitter; create calls never are."""

import random

import httpx
import pytest

from emi_copilot.core.resilient_http_client import (
    RetryPolicy,
)
from emi_copilot.core.upstream_errors import (
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from tests.unit.core.resilient_client_harness import (
    DEPENDENCY_NAME,
    RANDOM_SEED,
    ClientFactory,
    UpperBoundRandom,
    build_request,
)

# Idempotent calls


def test_send_idempotent_read_timeout_retries_up_to_max_attempts_then_raises_timeout(
    build_client_under_test: ClientFactory,
) -> None:
    """A status check that keeps timing out is tried max_attempts times, then gives up."""
    under_test = build_client_under_test([httpx.ReadTimeout], max_attempts=3)
    with pytest.raises(UpstreamTimeoutError) as raised_error:
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 3
    assert len(under_test.recorded_sleep_delays) == 2
    assert raised_error.value.is_outcome_unknown is True
    assert raised_error.value.dependency_name == DEPENDENCY_NAME
    assert isinstance(raised_error.value.__cause__, httpx.ReadTimeout)


def test_send_idempotent_transient_503_then_200_succeeds_on_second_attempt(
    build_client_under_test: ClientFactory,
) -> None:
    """A brief outage is ridden out: the retry gets the answer."""
    under_test = build_client_under_test([503, 200])
    response = under_test.client.send_idempotent(build_request())
    assert response.status_code == 200
    assert under_test.transport_call_count == 2
    assert len(under_test.recorded_sleep_delays) == 1


@pytest.mark.parametrize("client_error_status_code", [400, 404, 409, 422])
def test_send_idempotent_client_error_is_returned_without_retry(
    build_client_under_test: ClientFactory, client_error_status_code: int
) -> None:
    """A 4xx is the gateway's answer, not a fault; the adapter decides what it means."""
    under_test = build_client_under_test([client_error_status_code])
    response = under_test.client.send_idempotent(build_request())
    assert response.status_code == client_error_status_code
    assert under_test.transport_call_count == 1
    assert under_test.recorded_sleep_delays == []


@pytest.mark.parametrize("retryable_status_code", [502, 503, 504])
def test_send_idempotent_persistent_gateway_error_retries_then_raises_unavailable(
    build_client_under_test: ClientFactory, retryable_status_code: int
) -> None:
    """502, 503 and 504 are retried; after the last attempt the dependency is unavailable."""
    under_test = build_client_under_test([retryable_status_code], max_attempts=3)
    with pytest.raises(UpstreamUnavailableError) as raised_error:
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 3
    assert raised_error.value.status_code == retryable_status_code
    assert raised_error.value.is_outcome_unknown is False


@pytest.mark.parametrize("non_retryable_status_code", [500, 501])
def test_send_idempotent_other_server_error_raises_unavailable_without_retry(
    build_client_under_test: ClientFactory, non_retryable_status_code: int
) -> None:
    """Other 5xx statuses are failures but not transient, so they are not retried."""
    under_test = build_client_under_test([non_retryable_status_code])
    with pytest.raises(UpstreamUnavailableError) as raised_error:
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 1
    assert raised_error.value.status_code == non_retryable_status_code
    assert under_test.circuit_breaker.consecutive_failure_count == 1


def test_send_idempotent_refused_connection_retries_then_raises_timeout_with_known_outcome(
    build_client_under_test: ClientFactory,
) -> None:
    """A refused connection never reached the server, so the outcome is known."""
    under_test = build_client_under_test([httpx.ConnectError], max_attempts=2)
    with pytest.raises(UpstreamTimeoutError) as raised_error:
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 2
    assert raised_error.value.is_outcome_unknown is False


def test_send_idempotent_broken_connection_retries_then_raises_unavailable_outcome_unknown(
    build_client_under_test: ClientFactory,
) -> None:
    """A connection dropped mid-exchange is retried, and may have reached the server."""
    under_test = build_client_under_test([httpx.RemoteProtocolError], max_attempts=2)
    with pytest.raises(UpstreamUnavailableError) as raised_error:
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 2
    assert raised_error.value.is_outcome_unknown is True
    assert raised_error.value.status_code is None


def test_send_idempotent_undecodable_answer_raises_unavailable_without_retry(
    build_client_under_test: ClientFactory,
) -> None:
    """An answer that cannot be decoded is not a transport fault, so it is not retried."""
    under_test = build_client_under_test([httpx.DecodingError])
    with pytest.raises(UpstreamUnavailableError) as raised_error:
        under_test.client.send_idempotent(build_request())
    assert under_test.transport_call_count == 1
    assert raised_error.value.is_outcome_unknown is True


def test_send_idempotent_jitter_delays_stay_within_backoff_bounds_and_are_slept(
    build_client_under_test: ClientFactory,
) -> None:
    """Each retry sleeps a seeded uniform(0, min(max, base * 2^retry)) delay, in order."""
    under_test = build_client_under_test([httpx.ReadTimeout], max_attempts=5)
    with pytest.raises(UpstreamTimeoutError):
        under_test.client.send_idempotent(build_request())
    delay_ceilings_in_seconds = [0.1, 0.2, 0.3, 0.3]
    expected_random = random.Random(RANDOM_SEED)  # noqa: S311 - same seed as the client
    expected_delays = [expected_random.uniform(0, ceiling) for ceiling in delay_ceilings_in_seconds]
    assert under_test.recorded_sleep_delays == expected_delays
    for delay, ceiling in zip(
        under_test.recorded_sleep_delays, delay_ceilings_in_seconds, strict=True
    ):
        assert 0 <= delay <= ceiling


def test_retry_policy_delay_ceiling_doubles_from_base_and_is_capped_at_max() -> None:
    """The backoff ceiling is base, 2 x base, 4 x base, ... and never above max_delay."""
    retry_policy = RetryPolicy(max_attempts=6, base_delay_in_seconds=0.5, max_delay_in_seconds=3.0)
    ceilings = [
        retry_policy.compute_retry_delay_in_seconds(failed_attempt_number, UpperBoundRandom())
        for failed_attempt_number in range(1, 6)
    ]
    assert ceilings == [0.5, 1.0, 2.0, 3.0, 3.0]


@pytest.mark.parametrize(
    ("max_attempts", "base_delay_in_seconds", "max_delay_in_seconds"),
    [(0, 0.1, 1.0), (11, 0.1, 1.0), (3, 0.0, 1.0), (3, 2.0, 1.0)],
    ids=["no-attempts", "too-many-attempts", "zero-base-delay", "base-above-max"],
)
def test_retry_policy_with_unusable_values_raises_value_error(
    max_attempts: int, base_delay_in_seconds: float, max_delay_in_seconds: float
) -> None:
    """A policy that would never call, retry without bound or misorder its delays is refused."""
    with pytest.raises(ValueError, match="must"):
        RetryPolicy(
            max_attempts=max_attempts,
            base_delay_in_seconds=base_delay_in_seconds,
            max_delay_in_seconds=max_delay_in_seconds,
        )


# Non-idempotent calls: exactly one attempt, always


@pytest.mark.parametrize("timeout_after_sending", [httpx.ReadTimeout, httpx.WriteTimeout])
def test_send_non_idempotent_timeout_after_sending_makes_one_call_with_unknown_outcome(
    build_client_under_test: ClientFactory, timeout_after_sending: type[httpx.RequestError]
) -> None:
    """A create call that times out is never re-sent: the gateway may already have made a link."""
    under_test = build_client_under_test([timeout_after_sending, 200])
    with pytest.raises(UpstreamTimeoutError) as raised_error:
        under_test.client.send_non_idempotent(build_request())
    assert under_test.transport_call_count == 1
    assert under_test.recorded_sleep_delays == []
    assert raised_error.value.is_outcome_unknown is True


@pytest.mark.parametrize(
    "failure_before_sending", [httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout]
)
def test_send_non_idempotent_failure_before_sending_makes_one_call_with_known_outcome(
    build_client_under_test: ClientFactory, failure_before_sending: type[httpx.RequestError]
) -> None:
    """A create call whose connection never opened is not retried, and is known not to exist."""
    under_test = build_client_under_test([failure_before_sending, 200])
    with pytest.raises(UpstreamTimeoutError) as raised_error:
        under_test.client.send_non_idempotent(build_request())
    assert under_test.transport_call_count == 1
    assert raised_error.value.is_outcome_unknown is False


def test_send_non_idempotent_503_makes_one_call_and_raises_unavailable(
    build_client_under_test: ClientFactory,
) -> None:
    """Even a retry-worthy status is not retried for a create call."""
    under_test = build_client_under_test([503, 200])
    with pytest.raises(UpstreamUnavailableError) as raised_error:
        under_test.client.send_non_idempotent(build_request())
    assert under_test.transport_call_count == 1
    assert raised_error.value.status_code == 503


def test_send_non_idempotent_broken_connection_makes_one_call_with_unknown_outcome(
    build_client_under_test: ClientFactory,
) -> None:
    """A connection dropped after sending may have created the link, so it is outcome unknown."""
    under_test = build_client_under_test([httpx.ReadError, 200])
    with pytest.raises(UpstreamUnavailableError) as raised_error:
        under_test.client.send_non_idempotent(build_request())
    assert under_test.transport_call_count == 1
    assert raised_error.value.is_outcome_unknown is True


@pytest.mark.parametrize("answered_status_code", [201, 409])
def test_send_non_idempotent_answer_below_500_is_returned(
    build_client_under_test: ClientFactory, answered_status_code: int
) -> None:
    """Successes and 4xx answers go back to the adapter unchanged."""
    under_test = build_client_under_test([answered_status_code])
    response = under_test.client.send_non_idempotent(build_request())
    assert response.status_code == answered_status_code
    assert under_test.transport_call_count == 1
