"""POST /api/v1/payment-links: hands the chosen plan to the gateway, once per Idempotency-Key."""

from typing import Annotated

from fastapi import APIRouter, Body, Header, Request, Response

from emi_copilot.api.controllers.payment_status_controller import GET_PAYMENT_STATUS_ROUTE_NAME
from emi_copilot.api.dependencies import PaymentHandoffServiceDependency
from emi_copilot.api.openapi_documentation import (
    GATEWAY_FAILURE_PROBLEMS,
    GATEWAY_TIMEOUT_PROBLEM,
    MALFORMED_REQUEST_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
    UNAUTHENTICATED_NOTE,
    ProblemExample,
    describe_problem_responses,
)
from emi_copilot.dtos.payment_link_dtos import (
    IDEMPOTENCY_KEY_HEADER_DESCRIPTION,
    IDEMPOTENCY_KEY_PATTERN,
    MINIMUM_IDEMPOTENCY_KEY_LENGTH,
    CreatePaymentLinkRequest,
    PaymentLinkResponse,
)
from emi_copilot.services.payment_handoff_types import MAXIMUM_IDEMPOTENCY_KEY_LENGTH

payment_link_router = APIRouter(tags=["payment links"])

CREATE_PAYMENT_LINK_REQUEST_EXAMPLE = {
    "offerId": "mock-offer-card-6m",
    "priceInPaise": 2_200_000,
    "productId": "product-tv-43",
    "brandId": "brand-demo",
    "categoryId": "category-televisions",
}
PAYMENT_LINK_RESPONSE_EXAMPLE = {
    "orderId": "01JD5Z0Q8M6X3V2N7B4C9K1T0A",
    "paymentUrl": "https://mock-payments.invalid/pay/mock-link-0123456789abcdef0123",
    "status": "AWAITING_PAYMENT",
    "offer": {
        "offerId": "mock-offer-card-6m",
        "lenderLabel": "Your card's bank",
        "emiType": "STANDARD",
        "tenureInMonths": 6,
        "regularInstallmentInPaise": 385_000,
        "lastInstallmentInPaise": 385_000,
        "extraInTotalInPaise": 110_000,
        "totalPayableInPaise": 2_310_000,
        "priceInPaise": 2_200_000,
    },
}
PAYMENT_LINK_PROBLEMS = (
    ProblemExample(
        404,
        "OFFER_NOT_FOUND",
        "Offer not found",
        "The chosen offer is not quoted for this item and price.",
        "The gateway no longer quotes the chosen offer for this item and price.",
    ),
    ProblemExample(
        409,
        "PAYMENT_LINK_OUTCOME_UNKNOWN",
        "Payment link outcome unknown",
        "This key's payment link call has an unknown outcome; start again with a new key.",
        "A replay of a key whose first call has no usable link; start again with a new key, or "
        "wait while the first call is still running.",
    ),
    ProblemExample(
        409,
        "PAYMENT_LINK_CREATION_FAILED",
        "Payment link was not created",
        "This key's payment link was not created.",
        "",
    ),
    ProblemExample(
        409,
        "PAYMENT_LINK_CREATION_IN_PROGRESS",
        "Payment link creation in progress",
        "The first request with this key is running.",
        "",
    ),
    ProblemExample(
        422,
        "IDEMPOTENCY_KEY_REUSED",
        "Idempotency key reused",
        "The Idempotency-Key was used with a different body.",
        "The Idempotency-Key was already used with a different body.",
    ),
)


@payment_link_router.post(
    "/payment-links",
    status_code=201,
    summary="Create a payment link for the chosen plan",
    description=(
        "Re-quotes the chosen offer server-side, freezes its plan and asks the gateway for a "
        "payment link exactly once per Idempotency-Key; the call is never retried. The same key "
        "and body return the original 201 response. A gateway timeout answers 504 and the key "
        "then answers 409 PAYMENT_LINK_OUTCOME_UNKNOWN: start again with a new key (ADR 0005). "
        "Location points at the payment's status. " + UNAUTHENTICATED_NOTE
    ),
    response_description="The link was created (or this is the replay of its creation).",
    responses={
        201: {
            "content": {"application/json": {"example": PAYMENT_LINK_RESPONSE_EXAMPLE}},
            "headers": {
                "Location": {
                    "description": "The status URL of this payment.",
                    "schema": {"type": "string"},
                }
            },
        },
        **describe_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            REQUEST_VALIDATION_PROBLEM,
            *PAYMENT_LINK_PROBLEMS,
            *GATEWAY_FAILURE_PROBLEMS,
            GATEWAY_TIMEOUT_PROBLEM,
        ),
    },
)
def create_payment_link(
    payment_link_request: Annotated[
        CreatePaymentLinkRequest,
        Body(
            openapi_examples={
                "plan-b": {
                    "summary": "Design plan B on a ₹22,000 item",
                    "value": CREATE_PAYMENT_LINK_REQUEST_EXAMPLE,
                }
            }
        ),
    ],
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=MINIMUM_IDEMPOTENCY_KEY_LENGTH,
            max_length=MAXIMUM_IDEMPOTENCY_KEY_LENGTH,
            pattern=IDEMPOTENCY_KEY_PATTERN,
            description=IDEMPOTENCY_KEY_HEADER_DESCRIPTION,
            examples=["5f0c2a2e-6d1b-4c55-9a43-3f1b2f7f8e11"],
        ),
    ],
    request: Request,
    response: Response,
    payment_handoff_service: PaymentHandoffServiceDependency,
) -> PaymentLinkResponse:
    """Runs the hand-off for the body and key, and points Location at the payment's status."""
    handoff = payment_handoff_service.create_payment_link(
        payment_link_request.to_command(idempotency_key)
    )
    response.headers["Location"] = str(
        request.app.url_path_for(GET_PAYMENT_STATUS_ROUTE_NAME, orderId=handoff.order_id)
    )
    return PaymentLinkResponse.from_handoff(handoff)
