"""POST .../teach-back: advisory feedback on the customer's own words about a plan (C8)."""

from fastapi import APIRouter, Depends

from emi_copilot.api.controllers.customer_problem_examples import (
    CUSTOMER_OPERATION_NOTE,
    OFFER_NOT_QUOTED_PROBLEM,
    QUOTING_PROBLEMS,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_voice_problem_examples import (
    AI_SESSION_RATE_LIMITED_PROBLEM,
)
from emi_copilot.api.customer_request_context import (
    CustomerLanguageDependency,
    CustomerSessionCredentialsDependency,
)
from emi_copilot.api.customer_voice_dependencies import CustomerTeachBackServiceDependency
from emi_copilot.api.openapi_documentation import MALFORMED_REQUEST_PROBLEM
from emi_copilot.api.rate_limiting import enforce_ai_session_rate_limit
from emi_copilot.dtos.customer_teach_back_dtos import TeachBackRequest, TeachBackResponse

customer_teach_back_router = APIRouter(tags=["customer advice"])


@customer_teach_back_router.post(
    "/customer-sessions/{customerSessionId}/teach-back",
    summary="Check the customer's own words about a plan",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "Advisory only: CLOSE_ENOUGH when the "
        "monthly amount said is within 5% of the plan's and the months are right, otherwise "
        "TRY_AGAIN. The answer is read deterministically and never sent to an AI model; "
        "nothing is stored and consent is never blocked. Accept-Language en or ta picks the "
        "language of the feedback. highlightedAmounts are the engine's figures. Limited per "
        "client and session (429 with Retry-After)."
    ),
    response_description="The feedback card.",
    dependencies=[Depends(enforce_ai_session_rate_limit)],
    responses=describe_customer_problem_responses(
        MALFORMED_REQUEST_PROBLEM,
        *SESSION_PROBLEMS,
        OFFER_NOT_QUOTED_PROBLEM,
        AI_SESSION_RATE_LIMITED_PROBLEM,
        *QUOTING_PROBLEMS,
    ),
)
def check_customer_teach_back(
    teach_back_request: TeachBackRequest,
    credentials: CustomerSessionCredentialsDependency,
    language: CustomerLanguageDependency,
    teach_back_service: CustomerTeachBackServiceDependency,
) -> TeachBackResponse:
    """Scores the answer against the session's plan and gives the feedback card."""
    return TeachBackResponse.from_outcome(
        teach_back_service.check_for_session(
            credentials, teach_back_request.offer_id, teach_back_request.answer_text, language
        )
    )
