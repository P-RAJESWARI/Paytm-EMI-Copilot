"""GET /api/v1/payments/{orderId}/status: a payment's status, confirmed with the gateway."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from emi_copilot.api.dependencies import PaymentStatusServiceDependency
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.openapi_documentation import (
    GATEWAY_FAILURE_PROBLEMS,
    GATEWAY_TIMEOUT_PROBLEM,
    MERCHANT_AUTHENTICATION_PROBLEM,
    MERCHANT_PAYMENT_RATE_LIMITED_PROBLEM,
    PAYMENT_MERCHANT_BEARER_NOTE,
    REQUEST_VALIDATION_PROBLEM,
    ProblemExample,
    describe_problem_responses,
)
from emi_copilot.api.rate_limiting import enforce_merchant_payment_rate_limit
from emi_copilot.dtos.payment_status_dtos import PaymentStatusResponse
from emi_copilot.dtos.wire_types import MAXIMUM_IDENTIFIER_LENGTH, VISIBLE_ASCII_PATTERN

payment_status_router = APIRouter(tags=["payments"])

PAYMENT_STATUS_RESPONSE_EXAMPLE = {
    "orderId": "01JD5Z0Q8M6X3V2N7B4C9K1T0A",
    "status": "PAID",
    "amountPaidInPaise": 2_200_000,
}
PAYMENT_NOT_FOUND_PROBLEM = ProblemExample(
    404,
    "PAYMENT_ATTEMPT_NOT_FOUND",
    "Payment not found",
    "No payment attempt has order id 01JD5Z0Q8M6X3V2N7B4C9K1T0A.",
    "No payment of one of the shop's sales has this order id (another shop's, and a payment "
    "made for no sale, look the same).",
)


@payment_status_router.get(
    "/payments/{orderId}/status",
    dependencies=[Depends(enforce_merchant_payment_rate_limit)],
    summary="Get a payment's status",
    description=(
        "Asks the gateway about the order server-side, applies the answer and returns the "
        "public status: CREATING_LINK, LINK_FAILED, OUTCOME_UNKNOWN, AWAITING_PAYMENT, "
        "PAYMENT_PENDING, PAID or PAYMENT_FAILED. A client's word is never taken as a status. "
        "amountPaidInPaise is set only when paid. Only a payment of one of the signed-in shop's "
        "sales is answered; any other order id is 404. " + PAYMENT_MERCHANT_BEARER_NOTE
    ),
    response_description="The payment's current status.",
    responses={
        200: {"content": {"application/json": {"example": PAYMENT_STATUS_RESPONSE_EXAMPLE}}},
        **describe_problem_responses(
            PAYMENT_NOT_FOUND_PROBLEM,
            REQUEST_VALIDATION_PROBLEM,
            MERCHANT_AUTHENTICATION_PROBLEM,
            MERCHANT_PAYMENT_RATE_LIMITED_PROBLEM,
            *GATEWAY_FAILURE_PROBLEMS,
            GATEWAY_TIMEOUT_PROBLEM,
        ),
    },
)
def get_payment_status(
    order_id: Annotated[
        str,
        Path(
            alias="orderId",
            min_length=1,
            max_length=MAXIMUM_IDENTIFIER_LENGTH,
            pattern=VISIBLE_ASCII_PATTERN,
            description="The order id returned when the payment link was created.",
            examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0A"],
        ),
    ],
    current_merchant: CurrentMerchant,
    payment_status_service: PaymentStatusServiceDependency,
) -> PaymentStatusResponse:
    """Confirms the shop's order's status with the gateway and returns its public form."""
    return PaymentStatusResponse.from_view(
        payment_status_service.get_payment_status_for_merchant(
            current_merchant.merchant_id, order_id
        )
    )
