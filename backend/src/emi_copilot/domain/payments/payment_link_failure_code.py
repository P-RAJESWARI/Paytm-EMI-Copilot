"""Why a create-link call ended with no link, as stored on a LINK_CREATION_FAILED attempt."""

from enum import StrEnum

from emi_copilot.domain.errors import (
    PaymentGatewayRequestRejectedError,
    PaymentGatewayUnavailableError,
)


class PaymentLinkFailureCode(StrEnum):
    """A stable failure code; stored by value, so a rename or a new member needs a migration.

    GATEWAY_UNAVAILABLE means the request provably never left (ADR 0010 section 3). Every other
    code is the gateway's refusal reason, named exactly as in PaymentGatewayRejectionReason.
    """

    GATEWAY_UNAVAILABLE = "GATEWAY_UNAVAILABLE"
    INVALID_REQUEST = "INVALID_REQUEST"
    DUPLICATE_ORDER_ID = "DUPLICATE_ORDER_ID"
    OPERATION_NOT_PERMITTED = "OPERATION_NOT_PERMITTED"
    GATEWAY_INTERNAL_ERROR = "GATEWAY_INTERNAL_ERROR"


def find_payment_link_failure_code(
    error: PaymentGatewayUnavailableError | PaymentGatewayRequestRejectedError,
) -> PaymentLinkFailureCode:
    """Gives the code to store for a create-link call that certainly made no link."""
    if isinstance(error, PaymentGatewayRequestRejectedError):
        return PaymentLinkFailureCode(error.reason.value)
    return PaymentLinkFailureCode.GATEWAY_UNAVAILABLE
