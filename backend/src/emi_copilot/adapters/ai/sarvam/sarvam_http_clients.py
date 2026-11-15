"""Builds one breaker-guarded, never-retrying HTTP client per Sarvam capability."""

import random
import time
from dataclasses import dataclass
from datetime import timedelta

from emi_copilot.core.circuit_breaker import CircuitBreaker
from emi_copilot.core.clock import Clock
from emi_copilot.core.resilient_http_client import (
    ResilientHttpClient,
    RetryPolicy,
    UpstreamTimeouts,
    build_upstream_http_client,
)

# Sarvam calls go through send_non_idempotent only: they cost credits and every caller has a
# template fallback, so a failed call is never repeated. The policy is required but unused.
SINGLE_ATTEMPT_POLICY = RetryPolicy(
    max_attempts=1, base_delay_in_seconds=0.1, max_delay_in_seconds=0.1
)


@dataclass(frozen=True, slots=True)
class SarvamCallLimits:
    """The timeouts and breaker settings of one Sarvam capability, from AiSettings."""

    dependency_name: str
    connect_timeout_in_seconds: float
    read_timeout_in_seconds: float
    circuit_breaker_failure_threshold: int
    circuit_breaker_open_duration_in_seconds: float


def build_sarvam_http_client(limits: SarvamCallLimits, clock: Clock) -> ResilientHttpClient:
    """Builds the verified-TLS client and breaker of one capability, so it trips alone."""
    timeouts = UpstreamTimeouts(
        connect_timeout_in_seconds=limits.connect_timeout_in_seconds,
        read_timeout_in_seconds=limits.read_timeout_in_seconds,
        write_timeout_in_seconds=limits.read_timeout_in_seconds,
        pool_timeout_in_seconds=limits.connect_timeout_in_seconds,
    )
    circuit_breaker = CircuitBreaker(
        dependency_name=limits.dependency_name,
        failure_threshold=limits.circuit_breaker_failure_threshold,
        open_duration=timedelta(seconds=limits.circuit_breaker_open_duration_in_seconds),
        clock=clock,
    )
    return ResilientHttpClient(
        http_client=build_upstream_http_client(timeouts),
        retry_policy=SINGLE_ATTEMPT_POLICY,
        circuit_breaker=circuit_breaker,
        sleep=time.sleep,
        random_source=random.SystemRandom(),
    )
