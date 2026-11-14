"""Typed failures of calls to external dependencies, raised by the resilient HTTP client.

They are core-level on purpose: adapters translate them into domain errors at their boundary.
Messages name only the dependency, never a URL, query string, header or vendor payload.
"""


class UpstreamCallError(Exception):
    """Base class for a call to an external dependency that did not produce a usable response.

    is_outcome_unknown is True when the request may have reached the dependency, so a
    non-idempotent call (such as creating a payment link) may have taken effect (ADR 0005).
    """

    def __init__(self, dependency_name: str, detail: str, *, is_outcome_unknown: bool) -> None:
        """Stores the dependency's name, a payload-free explanation and the outcome certainty."""
        super().__init__(f"{dependency_name}: {detail}")
        self.dependency_name = dependency_name
        self.detail = detail
        self.is_outcome_unknown = is_outcome_unknown


class UpstreamTimeoutError(UpstreamCallError):
    """The dependency did not answer in time, or the connection to it could not be opened.

    is_outcome_unknown is False for connect and pool timeouts and refused connections, where the
    request never reached the server; True for read and write timeouts after it may have been sent.
    """


class UpstreamUnavailableError(UpstreamCallError):
    """The dependency failed to serve the call: a 5xx answer or a broken transport.

    status_code holds the 5xx status when the dependency answered, and None for a transport
    failure. A transport failure after the request may have been sent has is_outcome_unknown True.
    """

    def __init__(
        self,
        dependency_name: str,
        detail: str,
        *,
        is_outcome_unknown: bool,
        status_code: int | None,
    ) -> None:
        """Stores the failure like the base class and adds the dependency's 5xx status, if any."""
        super().__init__(dependency_name, detail, is_outcome_unknown=is_outcome_unknown)
        self.status_code = status_code


class CircuitOpenError(UpstreamCallError):
    """The circuit breaker rejected the call, so nothing was sent and the outcome is known."""

    def __init__(self, dependency_name: str) -> None:
        """Records which dependency's circuit is open; nothing reached it."""
        super().__init__(
            dependency_name,
            "call rejected because the circuit breaker is open",
            is_outcome_unknown=False,
        )
