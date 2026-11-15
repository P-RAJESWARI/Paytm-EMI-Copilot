"""POST .../explanation: the plain-words explanation of one plan in the customer's language (C7)."""

from fastapi import APIRouter

from emi_copilot.api.controllers.customer_problem_examples import (
    CUSTOMER_OPERATION_NOTE,
    OFFER_NOT_QUOTED_PROBLEM,
    QUOTING_PROBLEMS,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_response_examples import (
    PLAN_EXPLANATION_RESPONSE_EXAMPLE,
)
from emi_copilot.api.customer_dependencies import CustomerExplanationServiceDependency
from emi_copilot.api.customer_request_context import (
    CustomerLanguageDependency,
    CustomerSessionCredentialsDependency,
)
from emi_copilot.api.openapi_documentation import MALFORMED_REQUEST_PROBLEM
from emi_copilot.dtos.customer_explanation_dtos import (
    PlanExplanationRequest,
    PlanExplanationResponse,
)

customer_explanation_router = APIRouter(tags=["customer advice"])


@customer_explanation_router.post(
    "/customer-sessions/{customerSessionId}/explanation",
    summary="Explain one plan in plain words",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "The standard text (source TEMPLATE) "
        "about the plan as quoted now for the session's item: each month, for how many months, "
        "and the extra in total. Accept-Language en or ta picks the language (English by "
        "default; the Tamil text is a draft awaiting native review). Every rupee amount in the "
        "text is one of highlightedAmounts, computed by the engine, never by AI. Reading it "
        "changes nothing, so it can be asked again."
    ),
    response_description="The explanation and the two figures it mentions.",
    responses={
        200: {"content": {"application/json": {"example": PLAN_EXPLANATION_RESPONSE_EXAMPLE}}},
        **describe_customer_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            *SESSION_PROBLEMS,
            OFFER_NOT_QUOTED_PROBLEM,
            *QUOTING_PROBLEMS,
        ),
    },
)
def explain_customer_plan(
    explanation_request: PlanExplanationRequest,
    credentials: CustomerSessionCredentialsDependency,
    language: CustomerLanguageDependency,
    explanation_service: CustomerExplanationServiceDependency,
) -> PlanExplanationResponse:
    """Explains the chosen plan in the customer's language."""
    return PlanExplanationResponse.from_explanation(
        explanation_service.explain_for_session(credentials, explanation_request.offer_id, language)
    )
