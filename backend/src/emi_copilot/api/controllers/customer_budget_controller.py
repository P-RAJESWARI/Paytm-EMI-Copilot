"""PUT /api/v1/customer-sessions/{customerSessionId}/budget: the confirmed monthly budget (C2)."""

from fastapi import APIRouter

from emi_copilot.api.controllers.customer_problem_examples import (
    CONSENT_ALREADY_GIVEN_PROBLEM,
    CUSTOMER_OPERATION_NOTE,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_response_examples import BUDGET_RESPONSE_EXAMPLE
from emi_copilot.api.customer_dependencies import CustomerChoiceServiceDependency
from emi_copilot.api.customer_request_context import CustomerSessionCredentialsDependency
from emi_copilot.api.openapi_documentation import MALFORMED_REQUEST_PROBLEM
from emi_copilot.dtos.customer_budget_dtos import ConfirmBudgetRequest, ConfirmedBudgetResponse

customer_budget_router = APIRouter(tags=["customer sessions"])


@customer_budget_router.put(
    "/customer-sessions/{customerSessionId}/budget",
    summary="Confirm the customer's monthly budget",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "Stores the monthly amount the customer "
        "confirmed on screen; hasCustomerConfirmed must be true. A spoken amount counts only "
        "once the customer confirms it. Sending it again replaces the budget. Only while the "
        "plan is not yet agreed."
    ),
    response_description="The budget now held for the session.",
    responses={
        200: {"content": {"application/json": {"example": BUDGET_RESPONSE_EXAMPLE}}},
        **describe_customer_problem_responses(
            MALFORMED_REQUEST_PROBLEM, *SESSION_PROBLEMS, CONSENT_ALREADY_GIVEN_PROBLEM
        ),
    },
)
def confirm_customer_budget(
    budget_request: ConfirmBudgetRequest,
    credentials: CustomerSessionCredentialsDependency,
    choice_service: CustomerChoiceServiceDependency,
) -> ConfirmedBudgetResponse:
    """Stores the confirmed budget for the session."""
    return ConfirmedBudgetResponse.from_monthly_budget(
        choice_service.confirm_budget(credentials, budget_request.to_monthly_budget())
    )
