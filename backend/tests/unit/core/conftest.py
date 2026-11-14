"""Fixtures shared by the core tests: a factory for resilient clients on scripted transports."""

import random
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime

import httpx
import pytest

from emi_copilot.core.circuit_breaker import CircuitBreaker
from emi_copilot.core.resilient_http_client import ResilientHttpClient, RetryPolicy
from tests.fixed_clock import FixedClock
from tests.unit.core.resilient_client_harness import (
    DEPENDENCY_NAME,
    OPEN_DURATION,
    RANDOM_SEED,
    ClientFactory,
    ClientUnderTest,
    ScriptedOutcome,
    ScriptedTransport,
)


@pytest.fixture
def build_client_under_test() -> Iterator[ClientFactory]:
    """Yields a factory for clients under test and closes their httpx clients afterwards."""
    http_clients: list[httpx.Client] = []

    def build(
        outcomes: Sequence[ScriptedOutcome],
        *,
        max_attempts: int = 3,
        failure_threshold: int = 5,
    ) -> ClientUnderTest:
        """Builds a client whose transport plays back the outcomes; nothing really sleeps."""
        transport = ScriptedTransport(outcomes)
        http_client = httpx.Client(transport=httpx.MockTransport(transport.handle_request))
        http_clients.append(http_client)
        clock = FixedClock(datetime(2026, 11, 14, 10, 0, tzinfo=UTC))
        circuit_breaker = CircuitBreaker(
            dependency_name=DEPENDENCY_NAME,
            failure_threshold=failure_threshold,
            open_duration=OPEN_DURATION,
            clock=clock,
        )
        recorded_sleep_delays: list[float] = []
        client = ResilientHttpClient(
            http_client=http_client,
            retry_policy=RetryPolicy(
                max_attempts=max_attempts, base_delay_in_seconds=0.1, max_delay_in_seconds=0.3
            ),
            circuit_breaker=circuit_breaker,
            sleep=recorded_sleep_delays.append,
            random_source=random.Random(RANDOM_SEED),  # noqa: S311 - seeded jitter, not security
        )
        return ClientUnderTest(client, transport, circuit_breaker, clock, recorded_sleep_delays)

    yield build
    for http_client in http_clients:
        http_client.close()
