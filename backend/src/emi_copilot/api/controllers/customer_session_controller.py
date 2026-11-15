"""POST /api/v1/customer-sessions and GET .../{customerSessionId}: the QR-opened session (C1)."""

from fastapi import APIRouter, Depends, Request, Response

from emi_copilot.api.controllers.customer_problem_examples import (
    CUSTOMER_OPERATION_NOTE,
    CUSTOMER_QR_TOKEN_INVALID_PROBLEM,
    QR_EXCHANGE_RATE_LIMITED_PROBLEM,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_response_examples import (
    CUSTOMER_SESSION_RESPONSE_EXAMPLE,
    CUSTOMER_SESSION_SUMMARY_RESPONSE_EXAMPLE,
)
from emi_copilot.api.customer_dependencies import CustomerSessionServiceDependency
from emi_copilot.api.customer_request_context import CustomerSessionCredentialsDependency
from emi_copilot.api.openapi_documentation import (
    MALFORMED_REQUEST_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
)
from emi_copilot.api.rate_limiting import enforce_customer_session_start_rate_limit
from emi_copilot.dtos.customer_session_dtos import (
    CustomerSessionResponse,
    CustomerSessionSummaryResponse,
    StartCustomerSessionRequest,
)

customer_session_router = APIRouter(tags=["customer sessions"])

GET_CUSTOMER_SESSION_ROUTE_NAME = "get_customer_session"


@customer_session_router.post(
    "/customer-sessions",
    status_code=201,
    summary="Start a customer session from the shop's QR",
    description=(
        CUSTOMER_OPERATION_NOTE + "No credentials: the QR token itself is the credential. It is "
        "single-use: it is traded once for a session token, sent as X-Customer-Session-Token on "
        "every later call, and a second exchange of the same QR answers 401 (ADR 0022). A new "
        "QR from the shop ends the sale's earlier session. Limited per client address (429 with "
        "Retry-After). Location points at the session."
    ),
    response_description="The session for C1: shop, item and price.",
    dependencies=[Depends(enforce_customer_session_start_rate_limit)],
    responses={
        201: {
            "content": {"application/json": {"example": CUSTOMER_SESSION_RESPONSE_EXAMPLE}},
            "headers": {
                "Location": {
                    "description": "The URL of this customer session.",
                    "schema": {"type": "string"},
                }
            },
        },
        **describe_customer_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            REQUEST_VALIDATION_PROBLEM,
            CUSTOMER_QR_TOKEN_INVALID_PROBLEM,
            QR_EXCHANGE_RATE_LIMITED_PROBLEM,
        ),
    },
)
def start_customer_session(
    start_request: StartCustomerSessionRequest,
    request: Request,
    response: Response,
    session_service: CustomerSessionServiceDependency,
) -> CustomerSessionResponse:
    """Exchanges the QR for a session, returns its token and points Location at the session."""
    started_session = session_service.start(start_request.qr_token)
    response.headers["Location"] = str(
        request.app.url_path_for(
            GET_CUSTOMER_SESSION_ROUTE_NAME, customerSessionId=started_session.customer_session_id
        )
    )
    return CustomerSessionResponse.from_started_session(started_session)


@customer_session_router.get(
    "/customer-sessions/{customerSessionId}",
    name=GET_CUSTOMER_SESSION_ROUTE_NAME,
    summary="Get the customer session and the customer's progress",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "The C1 facts (shop, item, price, "
        "session code, expiry) and the customer's own progress: whether the budget is "
        "confirmed, the comfort check answer (null before answering) and whether consent was "
        "given. The token is never returned. A token used with another session's id answers 404."
    ),
    response_description="The session summary.",
    responses={
        200: {
            "content": {"application/json": {"example": CUSTOMER_SESSION_SUMMARY_RESPONSE_EXAMPLE}}
        },
        **describe_customer_problem_responses(*SESSION_PROBLEMS),
    },
)
def get_customer_session(
    credentials: CustomerSessionCredentialsDependency,
    session_service: CustomerSessionServiceDependency,
) -> CustomerSessionSummaryResponse:
    """Gives the session summary for its own token."""
    return CustomerSessionSummaryResponse.from_summary(session_service.get_summary(credentials))
