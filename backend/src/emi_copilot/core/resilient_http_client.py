"""Shared HTTP client for external dependencies: timeouts, verified TLS, retries and a breaker.

Adapters send through it and translate its core-level UpstreamCallError subclasses into domain
errors. Requests are logged as events with method, host and path only, never the query string,
headers or bodies, because a query may carry a merchant identifier.
"""

import logging
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import httpx

from emi_copilot.core.circuit_breaker import CallPermit, CircuitBreaker
from emi_copilot.core.upstream_errors import (
    CircuitOpenError,
    UpstreamCallError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)

resilient_http_client_logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = frozenset({502, 503, 504})
FIRST_SERVER_ERROR_STATUS_CODE = 500
# An upper bound keeps the exponential backoff ceiling finite and the worst-case latency sane.
MAXIMUM_ALLOWED_ATTEMPTS = 10
MINIMUM_TLS_VERSION = ssl.TLSVersion.TLSv1_2
# Failures that happen before any byte of the request can have reached the server.
FAILURES_BEFORE_SENDING = (httpx.ConnectTimeout, httpx.PoolTimeout, httpx.ConnectError)
CIRCUIT_OPEN_FAILURE_REASON = "circuit_open"


class RandomSource(Protocol):
    """Anything that draws a uniform random number, such as random.SystemRandom."""

    def uniform(self, a: float, b: float) -> float:
        """Returns a random number between a and b."""
        ...


@dataclass(frozen=True)
class UpstreamTimeouts:
    """The four httpx timeouts for one dependency, so no phase of a call can wait forever."""

    connect_timeout_in_seconds: float
    read_timeout_in_seconds: float
    write_timeout_in_seconds: float
    pool_timeout_in_seconds: float

    def __post_init__(self) -> None:
        """Rejects any timeout that is not positive."""
        timeouts_in_seconds = (
            self.connect_timeout_in_seconds,
            self.read_timeout_in_seconds,
            self.write_timeout_in_seconds,
            self.pool_timeout_in_seconds,
        )
        if min(timeouts_in_seconds) <= 0:
            raise ValueError("every upstream timeout must be positive")

    def to_httpx_timeout(self) -> httpx.Timeout:
        """Gives the explicit httpx timeout configuration for these values."""
        return httpx.Timeout(
            connect=self.connect_timeout_in_seconds,
            read=self.read_timeout_in_seconds,
            write=self.write_timeout_in_seconds,
            pool=self.pool_timeout_in_seconds,
        )


@dataclass(frozen=True)
class RetryPolicy:
    """How often and how patiently an idempotent call is retried (full-jitter backoff)."""

    max_attempts: int
    base_delay_in_seconds: float
    max_delay_in_seconds: float

    def __post_init__(self) -> None:
        """Rejects attempt counts outside 1 to 10 and delays that are not positive and ordered."""
        if not 1 <= self.max_attempts <= MAXIMUM_ALLOWED_ATTEMPTS:
            raise ValueError(f"max_attempts must be between 1 and {MAXIMUM_ALLOWED_ATTEMPTS}")
        if not 0 < self.base_delay_in_seconds <= self.max_delay_in_seconds:
            raise ValueError("delays must be positive and base_delay must not exceed max_delay")

    def compute_retry_delay_in_seconds(
        self, failed_attempt_number: int, random_source: RandomSource
    ) -> float:
        """Draws uniform(0, min(max_delay, base_delay * 2^retry_index)); retry_index starts at 0."""
        retry_index = failed_attempt_number - 1
        delay_ceiling_in_seconds = min(
            self.max_delay_in_seconds, self.base_delay_in_seconds * 2**retry_index
        )
        return random_source.uniform(0, delay_ceiling_in_seconds)


@dataclass(frozen=True)
class AttemptFailure:
    """Why one attempt produced no usable response, and whether trying again could help."""

    error: UpstreamCallError
    failure_reason: str
    is_retryable: bool
    cause: Exception | None = None
    status_code: int | None = None


def create_verified_tls_context() -> ssl.SSLContext:
    """Builds a TLS 1.2+ context that verifies certificates and host names; never relaxed."""
    tls_context = httpx.create_ssl_context(verify=True)
    tls_context.minimum_version = MINIMUM_TLS_VERSION
    return tls_context


def build_upstream_http_client(timeouts: UpstreamTimeouts) -> httpx.Client:
    """Creates the httpx client for one dependency with explicit timeouts and verified TLS."""
    return httpx.Client(
        timeout=timeouts.to_httpx_timeout(),
        transport=httpx.HTTPTransport(verify=create_verified_tls_context()),
    )


def classify_transport_failure(dependency_name: str, error: httpx.HTTPError) -> AttemptFailure:
    """Turns an httpx exception into a core error that says whether the request may have arrived."""
    if isinstance(error, FAILURES_BEFORE_SENDING):
        upstream_error: UpstreamCallError = UpstreamTimeoutError(
            dependency_name,
            "connection was refused or not opened in time; the request was not sent",
            is_outcome_unknown=False,
        )
    elif isinstance(error, httpx.TimeoutException):
        upstream_error = UpstreamTimeoutError(
            dependency_name,
            "no answer in time after the request may have been sent",
            is_outcome_unknown=True,
        )
    else:
        upstream_error = UpstreamUnavailableError(
            dependency_name,
            "transport failed after the request may have been sent",
            is_outcome_unknown=True,
            status_code=None,
        )
    return AttemptFailure(
        error=upstream_error,
        failure_reason=type(error).__name__,
        is_retryable=isinstance(error, httpx.TransportError),
        cause=error,
    )


def classify_server_error(dependency_name: str, status_code: int) -> AttemptFailure:
    """Turns a 5xx answer into a core error; only 502, 503 and 504 are worth retrying."""
    return AttemptFailure(
        error=UpstreamUnavailableError(
            dependency_name,
            f"answered with server error status {status_code}",
            is_outcome_unknown=False,
            status_code=status_code,
        ),
        failure_reason=f"http_status_{status_code}",
        is_retryable=status_code in RETRYABLE_STATUS_CODES,
        status_code=status_code,
    )


# Pattern: Retry with jittered backoff behind a Circuit Breaker. Reads ride out brief gateway
# hiccups without synchronised retry storms; a failing gateway is cut off instead of starving us.
class ResilientHttpClient:
    """Sends requests to one dependency; only idempotent requests are ever retried.

    Responses below 500 are returned to the caller, which decides what a 4xx means; they count as
    healthy for the breaker. Every 5xx and transport failure is recorded on the breaker.
    """

    def __init__(
        self,
        *,
        http_client: httpx.Client,
        retry_policy: RetryPolicy,
        circuit_breaker: CircuitBreaker,
        sleep: Callable[[float], None],
        random_source: RandomSource,
    ) -> None:
        """Keeps the httpx client, policy and breaker; the breaker names the dependency for both."""
        self._http_client = http_client
        self._dependency_name = circuit_breaker.dependency_name
        self._retry_policy = retry_policy
        self._circuit_breaker = circuit_breaker
        self._sleep = sleep
        self._random_source = random_source

    def send_idempotent(self, request: httpx.Request) -> httpx.Response:
        """Sends a read or status check, retrying timeouts, transport errors and 502/503/504."""
        attempt_number = 1
        while True:
            attempt_result = self._send_single_attempt(request)
            if isinstance(attempt_result, httpx.Response):
                return attempt_result
            is_last_attempt = attempt_number >= self._retry_policy.max_attempts
            if is_last_attempt or not attempt_result.is_retryable:
                self._log_attempt_event(
                    "upstream call failed", request, attempt_number, attempt_result
                )
                raise attempt_result.error from attempt_result.cause
            retry_delay_in_seconds = self._retry_policy.compute_retry_delay_in_seconds(
                attempt_number, self._random_source
            )
            self._log_attempt_event(
                "upstream call retry scheduled",
                request,
                attempt_number,
                attempt_result,
                retry_delay_in_seconds=retry_delay_in_seconds,
            )
            self._sleep(retry_delay_in_seconds)
            attempt_number += 1

    def send_non_idempotent(self, request: httpx.Request) -> httpx.Response:
        """Sends an initiate or create call exactly once; it is never retried, for any reason."""
        attempt_result = self._send_single_attempt(request)
        if isinstance(attempt_result, httpx.Response):
            return attempt_result
        self._log_attempt_event("upstream call failed", request, 1, attempt_result)
        raise attempt_result.error from attempt_result.cause

    def _send_single_attempt(self, request: httpx.Request) -> httpx.Response | AttemptFailure:
        """Makes one guarded attempt and returns the usable response or why there is none."""
        try:
            permit = self._circuit_breaker.acquire_call_permit()
            response = self._send_and_record_on_breaker(request, permit)
        except CircuitOpenError as error:
            return AttemptFailure(
                error=error, failure_reason=CIRCUIT_OPEN_FAILURE_REASON, is_retryable=False
            )
        except httpx.HTTPError as error:
            return classify_transport_failure(self._dependency_name, error)
        if response.status_code >= FIRST_SERVER_ERROR_STATUS_CODE:
            return classify_server_error(self._dependency_name, response.status_code)
        return response

    def _send_and_record_on_breaker(
        self, request: httpx.Request, permit: CallPermit
    ) -> httpx.Response:
        """Sends once; records success below 500 and failure otherwise, even if sending raises."""
        is_healthy_answer = False
        try:
            response = self._http_client.send(request)
            is_healthy_answer = response.status_code < FIRST_SERVER_ERROR_STATUS_CODE
            return response
        finally:
            if is_healthy_answer:
                self._circuit_breaker.record_success(permit)
            else:
                self._circuit_breaker.record_failure(permit)

    def _log_attempt_event(
        self,
        message: str,
        request: httpx.Request,
        attempt_number: int,
        attempt_failure: AttemptFailure,
        **event_fields: object,
    ) -> None:
        """Logs one structured event with the URL's host and path only, never query or payload."""
        resilient_http_client_logger.warning(
            message,
            extra={
                "dependency_name": self._dependency_name,
                "attempt_number": attempt_number,
                "failure_reason": attempt_failure.failure_reason,
                "http_status_code": attempt_failure.status_code,
                "is_outcome_unknown": attempt_failure.error.is_outcome_unknown,
                "http_method": request.method,
                "upstream_host": request.url.host,
                "upstream_path": request.url.path,
                **event_fields,
            },
        )
