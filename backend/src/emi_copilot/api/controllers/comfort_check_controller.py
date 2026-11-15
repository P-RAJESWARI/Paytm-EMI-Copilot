"""POST .../comfort-check: the customer allows or skips the comfort check (C3)."""

from fastapi import APIRouter

from emi_copilot.api.controllers.customer_problem_examples import (
    BUDGET_NOT_CONFIRMED_PROBLEM,
    CONSENT_ALREADY_GIVEN_PROBLEM,
    CUSTOMER_OPERATION_NOTE,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_response_examples import (
    COMFORT_CHECK_RESPONSE_EXAMPLE,
)
from emi_copilot.api.customer_dependencies import CustomerChoiceServiceDependency
from emi_copilot.api.customer_request_context import CustomerSessionCredentialsDependency
from emi_copilot.api.openapi_documentation import MALFORMED_REQUEST_PROBLEM
from emi_copilot.dtos.comfort_check_dtos import ComfortCheckRequest, ComfortCheckResponse

comfort_check_router = APIRouter(tags=["customer advice"])


@comfort_check_router.post(
    "/customer-sessions/{customerSessionId}/comfort-check",
    summary="Allow or skip the comfort check",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "With consent, reads the customer's "
        "synthetic monthly inflow and existing EMIs and returns them to the customer; they are "
        "not stored and the shop never sees them. Skipping reads nothing and plans then show "
        "without bands. The comfort check is advice, not a credit decision. Needs the confirmed "
        "budget."
    ),
    response_description="COMPLETED with the customer's figures, or SKIPPED with none.",
    responses={
        200: {"content": {"application/json": {"example": COMFORT_CHECK_RESPONSE_EXAMPLE}}},
        **describe_customer_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            *SESSION_PROBLEMS,
            BUDGET_NOT_CONFIRMED_PROBLEM,
            CONSENT_ALREADY_GIVEN_PROBLEM,
        ),
    },
)
def run_comfort_check(
    comfort_check_request: ComfortCheckRequest,
    credentials: CustomerSessionCredentialsDependency,
    choice_service: CustomerChoiceServiceDependency,
) -> ComfortCheckResponse:
    """Records the customer's choice and reads the profile only with consent."""
    return ComfortCheckResponse.from_outcome(
        choice_service.record_comfort_check_choice(
            credentials, has_customer_consented=comfort_check_request.has_customer_consented
        )
    )
