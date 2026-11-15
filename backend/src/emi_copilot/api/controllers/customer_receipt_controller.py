"""GET .../receipt: the C10 receipt after consent; there is no payment URL."""

from fastapi import APIRouter

from emi_copilot.api.controllers.customer_problem_examples import (
    CONSENT_NOT_GIVEN_PROBLEM,
    CUSTOMER_OPERATION_NOTE,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_response_examples import RECEIPT_RESPONSE_EXAMPLE
from emi_copilot.api.customer_dependencies import CustomerReceiptServiceDependency
from emi_copilot.api.customer_request_context import CustomerSessionCredentialsDependency
from emi_copilot.dtos.customer_receipt_dtos import CustomerReceiptResponse

customer_receipt_router = APIRouter(tags=["customer consent"])

GET_CUSTOMER_RECEIPT_ROUTE_NAME = "get_customer_receipt"


@customer_receipt_router.get(
    "/customer-sessions/{customerSessionId}/receipt",
    name=GET_CUSTOMER_RECEIPT_ROUTE_NAME,
    summary="Get the receipt after consent",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "READY_TO_PAY means the shop now takes "
        "payment on Paytm; PAYMENT_PENDING means the shop started a payment whose outcome is "
        "not known yet; PAID is confirmed server-side; PAYMENT_NOT_COMPLETED explains the next "
        "step. The cooling-off wording is a placeholder until the lender confirms its period. "
        "There is no payment URL."
    ),
    response_description="The receipt with the frozen plan.",
    responses={
        200: {"content": {"application/json": {"example": RECEIPT_RESPONSE_EXAMPLE}}},
        **describe_customer_problem_responses(*SESSION_PROBLEMS, CONSENT_NOT_GIVEN_PROBLEM),
    },
)
def get_customer_receipt(
    credentials: CustomerSessionCredentialsDependency,
    receipt_service: CustomerReceiptServiceDependency,
) -> CustomerReceiptResponse:
    """Gives the session's receipt."""
    return CustomerReceiptResponse.from_receipt(receipt_service.get_receipt(credentials))
