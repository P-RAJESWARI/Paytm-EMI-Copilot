"""Shared test harness for the resilient HTTP client: scripted transport and constants."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta

import httpx

from emi_copilot.core.circuit_breaker import CircuitBreaker, CircuitState
from emi_copilot.core.resilient_http_client import ResilientHttpClient
from tests.fixed_clock import FixedClock

DEPENDENCY_NAME = "test-gateway"
SYNTHETIC_QUERY_VALUE = "SYNTHETIC-MERCHANT-REF-0001"
REQUEST_URL = f"https://gateway.example.test/v1/order/status?merchantRef={SYNTHETIC_QUERY_VALUE}"
OPEN_DURATION = timedelta(seconds=30)
RANDOM_SEED = 20261114
CLIENT_LOGGER_NAME = "emi_copilot.core.resilient_http_client"

# A scripted outcome is a status code to answer with or an httpx error class to raise.
ScriptedOutcome = int | type[httpx.RequestError]


def read_state(circuit_breaker: CircuitBreaker) -> CircuitState:
    """Reads the breaker's state through a call, so type checkers do not narrow it across steps."""
    return circuit_breaker.state


class ScriptedTransport:
    """Answers each request with the next scripted outcome; the last one repeats forever."""

    def __init__(self, outcomes: Sequence[ScriptedOutcome]) -> None:
        """Keeps the outcomes to play back and starts with no requests received."""
        self._outcomes = list(outcomes)
        self.received_requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Records the request, then answers or raises as scripted."""
        self.received_requests.append(request)
        outcome = self._outcomes[min(len(self.received_requests), len(self._outcomes)) - 1]
        if isinstance(outcome, int):
            return httpx.Response(outcome, json={"synthetic": True})
        raise outcome("synthetic transport failure", request=request)


@dataclass
class ClientUnderTest:
    """A resilient client wired to a scripted transport, a fixed clock and a recording sleep."""

    client: ResilientHttpClient
    transport: ScriptedTransport
    circuit_breaker: CircuitBreaker
    clock: FixedClock
    recorded_sleep_delays: list[float]

    @property
    def transport_call_count(self) -> int:
        """Gives how many requests actually reached the transport."""
        return len(self.transport.received_requests)


ClientFactory = Callable[..., ClientUnderTest]


def build_request() -> httpx.Request:
    """Builds a request whose query string stands in for a merchant identifier."""
    return httpx.Request("POST", REQUEST_URL, json={"orderId": "ORDER-0001"})


class UpperBoundRandom:
    """Random source that always draws the upper bound, exposing the backoff ceiling."""

    def uniform(self, a: float, b: float) -> float:  # noqa: ARG002 - matches RandomSource
        """Always draws the upper bound b, the largest value a uniform draw could give."""
        return b
