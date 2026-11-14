"""POST /api/v1/customer-sessions: trades the QR token for a session bound to one sale (C1)."""

from fastapi import APIRouter

from emi_copilot.api.controllers.customer_flow_service_providers import (
    CustomerSessionServiceDependency,
)
from emi_copilot.api.controllers.customer_problem_examples import (
    CUSTOMER_QR_TOKEN_INVALID_PROBLEM,
    STUB_OPERATION_NOTE,
)
from emi_copilot.api.controllers.customer_response_examples import (
    CUSTOMER_SESSION_RESPONSE_EXAMPLE,
)
from emi_copilot.api.openapi_documentation import (
    MALFORMED_REQUEST_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
    describe_problem_responses,
)
from emi_copilot.dtos.customer_session_dtos import (
    CustomerSessionResponse,
    StartCustomerSessionRequest,
)

customer_session_router = APIRouter(tags=["customer sessions"])


@customer_session_router.post(
    "/customer-sessions",
    status_code=201,
    summary="Start a customer session from the shop's QR",
    description=(
        STUB_OPERATION_NOTE + "Trades the QR token for a session token, sent as "
        "X-Customer-Session-Token on every later call. Sample tokens: stub-qr-4821 (the "
        "design's customer) and stub-qr-4822 (the second, Risky example). Scanning a sample QR "
        "again restarts its sample session; the earlier token stops working."
    ),
    response_description="The session for C1: shop, item and price.",
    responses={
        201: {"content": {"application/json": {"example": CUSTOMER_SESSION_RESPONSE_EXAMPLE}}},
        **describe_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            REQUEST_VALIDATION_PROBLEM,
            CUSTOMER_QR_TOKEN_INVALID_PROBLEM,
        ),
    },
)
def start_customer_session(
    start_request: StartCustomerSessionRequest,
    session_service: CustomerSessionServiceDependency,
) -> CustomerSessionResponse:
    """Opens the QR's session and returns its token."""
    return CustomerSessionResponse.from_started_session(
        session_service.start_session(start_request.qr_token)
    )
