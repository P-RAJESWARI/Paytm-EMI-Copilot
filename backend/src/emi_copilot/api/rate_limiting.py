"""Request rate limits applied as FastAPI dependencies, before the endpoint or its body runs.

The limiters themselves are built once at startup (api/dependencies.py) and kept on the
application components; the providers here hand them out.

Merchant calls are keyed by the signed-in shop, after its token is checked. Unauthenticated
calls (pairing, gateway webhooks) are keyed by the connection's peer address. X-Forwarded-For
is not trusted, because a client could set it freely; behind a proxy, the proxy must be
configured to pass the address.
"""

from typing import Annotated

from fastapi import Depends, Request

from emi_copilot.api.dependencies import ComponentsDependency
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.core.fixed_window_rate_limiter import FixedWindowRateLimiter
from emi_copilot.domain.errors import RequestRateLimitedError

UNKNOWN_CLIENT_ADDRESS = "unknown-client"


def provide_pairing_rate_limiter(components: ComponentsDependency) -> FixedWindowRateLimiter:
    """Gives the one pairing rate limiter, whose counts span requests."""
    return components.pairing_rate_limiter


def provide_merchant_payment_rate_limiter(
    components: ComponentsDependency,
) -> FixedWindowRateLimiter:
    """Gives the one per-shop limiter of gateway-backed merchant calls."""
    return components.merchant_payment_rate_limiter


def provide_payment_webhook_rate_limiter(
    components: ComponentsDependency,
) -> FixedWindowRateLimiter:
    """Gives the one per-client limiter of gateway webhooks."""
    return components.payment_webhook_rate_limiter


PairingRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_pairing_rate_limiter)
]
MerchantPaymentRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_merchant_payment_rate_limiter)
]
PaymentWebhookRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_payment_webhook_rate_limiter)
]


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


def enforce_merchant_payment_rate_limit(
    current_merchant: CurrentMerchant,
    merchant_payment_rate_limiter: MerchantPaymentRateLimiterDependency,
) -> None:
    """Counts one gateway-backed call for the shop and refuses it with 429 when over the limit."""
    decision = merchant_payment_rate_limiter.try_acquire(current_merchant.merchant_id)
    if not decision.is_allowed:
        raise RequestRateLimitedError(
            decision.retry_after_in_seconds,
            "Too many payment requests from this shop; try again after Retry-After.",
        )


def enforce_payment_webhook_rate_limit(
    request: Request, payment_webhook_rate_limiter: PaymentWebhookRateLimiterDependency
) -> None:
    """Counts one webhook for the client, before its body is read; 429 when over the limit."""
    decision = payment_webhook_rate_limiter.try_acquire(find_client_address(request))
    if not decision.is_allowed:
        raise RequestRateLimitedError(
            decision.retry_after_in_seconds,
            "Too many webhook requests from this client; try again after Retry-After.",
        )
