"""Request rate limits applied as FastAPI dependencies, before the endpoint or its body runs.

The client is keyed by the connection's peer address. X-Forwarded-For is not trusted, because
a client could set it freely; behind a proxy, the proxy must be configured to pass the address.
"""

from fastapi import Request

from emi_copilot.api.dependencies import PairingRateLimiterDependency
from emi_copilot.domain.errors import RequestRateLimitedError

UNKNOWN_CLIENT_ADDRESS = "unknown-client"


def find_client_address(request: Request) -> str:
    """Gives the peer address of the request's connection, or a shared key when it is unknown."""
    return request.client.host if request.client is not None else UNKNOWN_CLIENT_ADDRESS


def enforce_pairing_rate_limit(
    request: Request, pairing_rate_limiter: PairingRateLimiterDependency
) -> None:
    """Counts one pairing request for the client and refuses it with 429 when over the limit."""
    decision = pairing_rate_limiter.try_acquire(find_client_address(request))
    if not decision.is_allowed:
        raise RequestRateLimitedError(
            decision.retry_after_in_seconds,
            "Too many pairing requests from this client; try again after Retry-After.",
        )
