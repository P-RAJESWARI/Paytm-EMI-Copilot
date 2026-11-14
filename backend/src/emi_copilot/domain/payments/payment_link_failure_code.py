"""Which failure code to store when a create-link call certainly made no link."""

from emi_copilot.domain.errors import (
    PaymentGatewayRequestRejectedError,
    PaymentGatewayUnavailableError,
    PaymentLinkFailureCode,
)


def find_payment_link_failure_code(
    error: PaymentGatewayUnavailableError | PaymentGatewayRequestRejectedError,
) -> PaymentLinkFailureCode:
    """Gives the code to store for a create-link call that certainly made no link."""
    if isinstance(error, PaymentGatewayRequestRejectedError):
        return PaymentLinkFailureCode(error.reason.value)
    return PaymentLinkFailureCode.GATEWAY_UNAVAILABLE
