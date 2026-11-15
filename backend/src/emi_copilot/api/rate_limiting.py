"""Request rate limits applied as FastAPI dependencies, before the endpoint or its body runs.

The limiters themselves are built once at startup (api/dependencies.py) and kept on the
application components; the providers here hand them out.

Merchant calls are keyed by the signed-in shop, after its token is checked. Unauthenticated
calls (pairing, gateway webhooks, the customer QR exchange) are keyed by the connection's peer
address. Customer one-time code requests and consent run before the session token is checked,
so they are keyed by the peer address and the path's session id together: a phone cannot use up
another session's allowance by naming its id, and a customer behind a shared mobile address is
not refused because of other customers. X-Forwarded-For is not trusted, because a client could
set it freely; behind a proxy, the proxy must be configured to pass the address.
"""

from typing import Annotated

from fastapi import Depends, Request

from emi_copilot.api.dependencies import ComponentsDependency
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.core.fixed_window_rate_limiter import FixedWindowRateLimiter
from emi_copilot.domain.errors import RequestRateLimitedError

UNKNOWN_CLIENT_ADDRESS = "unknown-client"
CUSTOMER_SESSION_ID_PATH_PARAMETER = "customerSessionId"


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


def provide_customer_session_start_rate_limiter(
    components: ComponentsDependency,
) -> FixedWindowRateLimiter:
    """Gives the one per-client limiter of customer QR exchanges."""
    return components.customer_session_start_rate_limiter


def provide_consent_otp_request_rate_limiter(
    components: ComponentsDependency,
) -> FixedWindowRateLimiter:
    """Gives the one limiter of consent one-time code requests per client and session."""
    return components.consent_otp_request_rate_limiter


def provide_customer_consent_rate_limiter(
    components: ComponentsDependency,
) -> FixedWindowRateLimiter:
    """Gives the one limiter of consent attempts (each verifies a code) per client and session."""
    return components.customer_consent_rate_limiter


def provide_ai_session_rate_limiter(components: ComponentsDependency) -> FixedWindowRateLimiter:
    """Gives the one limiter of AI calls (speech and teach-back) per client and session."""
    return components.ai_session_rate_limiter


PairingRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_pairing_rate_limiter)
]
MerchantPaymentRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_merchant_payment_rate_limiter)
]
PaymentWebhookRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_payment_webhook_rate_limiter)
]

CustomerSessionStartRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_customer_session_start_rate_limiter)
]
ConsentOtpRequestRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_consent_otp_request_rate_limiter)
]
CustomerConsentRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_customer_consent_rate_limiter)
]
AiSessionRateLimiterDependency = Annotated[
    FixedWindowRateLimiter, Depends(provide_ai_session_rate_limiter)
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


def find_client_and_customer_session_key(request: Request) -> str:
    """Gives the peer address and the path's customer session id as one rate-limit key."""
    customer_session_id = request.path_params.get(CUSTOMER_SESSION_ID_PATH_PARAMETER, "")
    return f"{find_client_address(request)} {customer_session_id}"


def enforce_customer_session_start_rate_limit(
    request: Request, limiter: CustomerSessionStartRateLimiterDependency
) -> None:
    """Counts one QR exchange for the client, before the token is checked; 429 when over."""
    decision = limiter.try_acquire(find_client_address(request))
    if not decision.is_allowed:
        raise RequestRateLimitedError(
            decision.retry_after_in_seconds,
            "Too many QR exchanges from this client; try again after Retry-After.",
        )


def enforce_consent_otp_request_rate_limit(
    request: Request, limiter: ConsentOtpRequestRateLimiterDependency
) -> None:
    """Counts one code request for the client and session; 429 when over the limit."""
    decision = limiter.try_acquire(find_client_and_customer_session_key(request))
    if not decision.is_allowed:
        raise RequestRateLimitedError(
            decision.retry_after_in_seconds,
            "Too many one-time code requests for this session; try again after Retry-After.",
        )


def enforce_customer_consent_rate_limit(
    request: Request, limiter: CustomerConsentRateLimiterDependency
) -> None:
    """Counts one consent attempt (a code check) for the client and session; 429 when over."""
    decision = limiter.try_acquire(find_client_and_customer_session_key(request))
    if not decision.is_allowed:
        raise RequestRateLimitedError(
            decision.retry_after_in_seconds,
            "Too many consent attempts for this session; try again after Retry-After.",
        )


def enforce_ai_session_rate_limit(
    request: Request, limiter: AiSessionRateLimiterDependency
) -> None:
    """Counts one voice or teach-back call for the client and session; 429 when over."""
    decision = limiter.try_acquire(find_client_and_customer_session_key(request))
    if not decision.is_allowed:
        raise RequestRateLimitedError(
            decision.retry_after_in_seconds,
            "Too many voice or teach-back requests for this session; try again after Retry-After.",
        )
