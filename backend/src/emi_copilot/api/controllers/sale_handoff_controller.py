"""M4 hand-off of an agreed sale: its EDC steps, a payment link and the confirmed payment state.

There is deliberately no endpoint that marks a sale paid (plan Q5): PAID comes only from a
gateway report confirmed server-side (security-and-compliance.md section 1).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response

from emi_copilot.api.controllers.payment_link_controller import PAYMENT_LINK_PROBLEMS
from emi_copilot.api.controllers.sale_controller import NO_STORE_HEADERS, SaleIdPath
from emi_copilot.api.controllers.sale_documentation import SALE_NOT_FOUND_PROBLEM
from emi_copilot.api.controllers.sale_handoff_documentation import (
    CHOSEN_PLAN_NO_LONGER_OFFERED_PROBLEM,
    PAID_SALE_PAYMENT_STATUS_EXAMPLE,
    PAYMENT_LINK_ALREADY_ACTIVE_PROBLEM,
    SALE_HANDOFF_EXAMPLE,
    SALE_HAS_NO_AGREED_PLAN_PROBLEM,
    SALE_PAYMENT_LINK_EXAMPLE,
    SALE_TAKES_NO_NEW_LINK_PROBLEM,
)
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.openapi_documentation import (
    GATEWAY_FAILURE_PROBLEMS,
    GATEWAY_TIMEOUT_PROBLEM,
    MERCHANT_AUTHENTICATION_PROBLEM,
    MERCHANT_BEARER_NOTE,
    MERCHANT_PAYMENT_RATE_LIMITED_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
    describe_problem_responses,
)
from emi_copilot.api.rate_limiting import enforce_merchant_payment_rate_limit
from emi_copilot.api.sale_dependencies import SaleHandoffServiceDependency
from emi_copilot.dtos.payment_link_dtos import (
    IDEMPOTENCY_KEY_HEADER_DESCRIPTION,
    IDEMPOTENCY_KEY_PATTERN,
    MINIMUM_IDEMPOTENCY_KEY_LENGTH,
)
from emi_copilot.dtos.sale_handoff_dtos import (
    SaleHandoffResponse,
    SalePaymentLinkResponse,
    SalePaymentStatusResponse,
)
from emi_copilot.services.payment_handoff_types import MAXIMUM_IDEMPOTENCY_KEY_LENGTH

sale_handoff_router = APIRouter(tags=["sales"])

GET_SALE_HANDOFF_ROUTE_NAME = "get_sale_handoff"
# Answers that carry a payment link are never cached.
PAYMENT_LINK_HEADERS = {
    "Location": {"description": "The sale's hand-off URL.", "schema": {"type": "string"}},
    "Cache-Control": {"description": "Always no-store.", "schema": {"type": "string"}},
}
SALE_HANDOFF_PROBLEMS = (
    REQUEST_VALIDATION_PROBLEM,
    MERCHANT_AUTHENTICATION_PROBLEM,
    SALE_NOT_FOUND_PROBLEM,
)


@sale_handoff_router.get(
    "/sales/{saleId}/handoff",
    name=GET_SALE_HANDOFF_ROUTE_NAME,
    summary="Read an agreed sale's payment hand-off",
    description=(
        "M4: the sale with its agreed plan (monthly, extra in total and total), the steps to "
        "key into the card machine (EDC; instructions only, nothing here can mark it paid), the "
        "latest payment link (null until one exists) and where the payment stands: WAITING, "
        "PAID or NOT_COMPLETED. paymentConfirmedAt is set only once PAID. A sale still CHOOSING, "
        "or EXPIRED, answers 409 SALE_STATE_CONFLICT. " + MERCHANT_BEARER_NOTE
    ),
    response_description="The hand-off.",
    responses={
        200: {"content": {"application/json": {"example": SALE_HANDOFF_EXAMPLE}}},
        **describe_problem_responses(*SALE_HANDOFF_PROBLEMS, SALE_HAS_NO_AGREED_PLAN_PROBLEM),
    },
)
def get_sale_handoff(
    sale_id: SaleIdPath,
    current_merchant: CurrentMerchant,
    response: Response,
    sale_handoff_service: SaleHandoffServiceDependency,
) -> SaleHandoffResponse:
    """Reads the signed-in shop's hand-off; the answer may carry a link, so it is not cached."""
    response.headers.update(NO_STORE_HEADERS)
    return SaleHandoffResponse.from_handoff_view(
        sale_handoff_service.get_handoff(current_merchant, sale_id)
    )


@sale_handoff_router.post(
    "/sales/{saleId}/payment-links",
    status_code=201,
    dependencies=[Depends(enforce_merchant_payment_rate_limit)],
    summary="Create a payment link for an agreed sale",
    description=(
        "Re-quotes the agreed plan server-side; if any figure differs from what the customer "
        "agreed to, answers 409 CHOSEN_PLAN_NO_LONGER_OFFERED. Allowed while READY_TO_PAY, or "
        "PAYMENT_NOT_COMPLETED (the sale first goes back to READY_TO_PAY). The gateway is asked "
        "exactly once per Idempotency-Key, never retried; the same key returns the original 201 "
        "body, a gateway timeout answers 504 and the key then answers 409 (ADR 0005). A new key "
        "while the latest link is being made, awaits payment or has an unknown outcome answers "
        "409 PAYMENT_LINK_ALREADY_ACTIVE; after a failed or refused link it makes a new one. "
        "Show the link on the tablet as a QR code and a copy button: nothing is sent to anyone. "
        "Limited "
        "per shop (429 with Retry-After). " + MERCHANT_BEARER_NOTE
    ),
    response_description="The link was created (or this is the replay of its creation).",
    responses={
        201: {
            "content": {"application/json": {"example": SALE_PAYMENT_LINK_EXAMPLE}},
            "headers": PAYMENT_LINK_HEADERS,
        },
        **describe_problem_responses(
            *SALE_HANDOFF_PROBLEMS,
            SALE_TAKES_NO_NEW_LINK_PROBLEM,
            CHOSEN_PLAN_NO_LONGER_OFFERED_PROBLEM,
            PAYMENT_LINK_ALREADY_ACTIVE_PROBLEM,
            *PAYMENT_LINK_PROBLEMS[1:],
            MERCHANT_PAYMENT_RATE_LIMITED_PROBLEM,
            *GATEWAY_FAILURE_PROBLEMS,
            GATEWAY_TIMEOUT_PROBLEM,
        ),
    },
)
def create_sale_payment_link(  # noqa: PLR0913 - mostly Annotated request parameter declarations
    *,
    sale_id: SaleIdPath,
    current_merchant: CurrentMerchant,
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
    sale_handoff_service: SaleHandoffServiceDependency,
) -> SalePaymentLinkResponse:
    """Hands the agreed plan to the gateway once per key and points Location at the hand-off."""
    handoff = sale_handoff_service.create_payment_link(current_merchant, sale_id, idempotency_key)
    response.headers.update(NO_STORE_HEADERS)
    response.headers["Location"] = str(
        request.app.url_path_for(GET_SALE_HANDOFF_ROUTE_NAME, saleId=sale_id)
    )
    return SalePaymentLinkResponse.from_handoff(handoff)


@sale_handoff_router.get(
    "/sales/{saleId}/payment-status",
    dependencies=[Depends(enforce_merchant_payment_rate_limit)],
    summary="Check an agreed sale's payment with the gateway",
    description=(
        "Asks the gateway server-side about the sale's latest payment link, applies the answer "
        "(a PAID answer moves the sale to PAID and the live stream announces it) and returns "
        "WAITING, PAID or NOT_COMPLETED. A client's word is never taken as a status. Limited "
        "per shop (429 with Retry-After). " + MERCHANT_BEARER_NOTE
    ),
    response_description="Where the payment stands now.",
    responses={
        200: {"content": {"application/json": {"example": PAID_SALE_PAYMENT_STATUS_EXAMPLE}}},
        **describe_problem_responses(
            *SALE_HANDOFF_PROBLEMS,
            SALE_HAS_NO_AGREED_PLAN_PROBLEM,
            MERCHANT_PAYMENT_RATE_LIMITED_PROBLEM,
            *GATEWAY_FAILURE_PROBLEMS,
            GATEWAY_TIMEOUT_PROBLEM,
        ),
    },
)
def check_sale_payment_status(
    sale_id: SaleIdPath,
    current_merchant: CurrentMerchant,
    sale_handoff_service: SaleHandoffServiceDependency,
) -> SalePaymentStatusResponse:
    """Confirms the payment with the gateway and gives its state."""
    return SalePaymentStatusResponse.from_view(
        sale_handoff_service.check_payment_status(current_merchant, sale_id)
    )
