"""GET .../plans (C4) and POST .../alternatives (C6): ranked plans and smarter options."""

from fastapi import APIRouter

from emi_copilot.api.controllers.customer_problem_examples import (
    BUDGET_NOT_CONFIRMED_PROBLEM,
    CONSENT_ALREADY_GIVEN_PROBLEM,
    CUSTOMER_OPERATION_NOTE,
    OFFER_NOT_QUOTED_PROBLEM,
    QUOTING_PROBLEMS,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_response_examples import (
    PLAN_ALTERNATIVES_RESPONSE_EXAMPLE,
    PLANS_RESPONSE_EXAMPLE,
)
from emi_copilot.api.customer_dependencies import CustomerPlanServiceDependency
from emi_copilot.api.customer_request_context import CustomerSessionCredentialsDependency
from emi_copilot.api.openapi_documentation import MALFORMED_REQUEST_PROBLEM
from emi_copilot.dtos.customer_plan_dtos import CustomerPlansResponse
from emi_copilot.dtos.plan_alternative_dtos import (
    PlanAlternativesRequest,
    PlanAlternativesResponse,
)

customer_plan_router = APIRouter(tags=["customer advice"])


@customer_plan_router.get(
    "/customer-sessions/{customerSessionId}/plans",
    summary="Compare every EMI plan for the budget",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "Lists every plan quoted for the item: "
        "plans within the budget first, then by amount above it, then by extra in total, "
        "tenure and offer id (ADR 0020). No plan is ever hidden: when none fits, all are "
        "listed with amountAboveBudgetInPaise. reasonCodes state facts only. comfort is null "
        "when the comfort check was skipped. Needs the confirmed budget."
    ),
    response_description="Every plan in order, with budget fit and comfort.",
    responses={
        200: {"content": {"application/json": {"example": PLANS_RESPONSE_EXAMPLE}}},
        **describe_customer_problem_responses(
            *SESSION_PROBLEMS,
            BUDGET_NOT_CONFIRMED_PROBLEM,
            CONSENT_ALREADY_GIVEN_PROBLEM,
            *QUOTING_PROBLEMS,
        ),
    },
)
def list_customer_plans(
    credentials: CustomerSessionCredentialsDependency,
    plan_service: CustomerPlanServiceDependency,
) -> CustomerPlansResponse:
    """Ranks the item's plans for the session's budget."""
    return CustomerPlansResponse.from_comparison(plan_service.compare_plans(credentials))


@customer_plan_router.post(
    "/customer-sessions/{customerSessionId}/alternatives",
    summary="Find smarter alternatives to a plan",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "Recomputes, with the EMI engine, a "
        "down payment (the gap to the budget over the plan's tenure, rounded up to ₹1,000), "
        "every longer plan for the item and the shop's cheaper model of the same brand. Every "
        "option is kept, even one that does not lower the monthly amount; "
        "hasLowerMonthlyAlternative false is the 'nothing better' state. Only LONGER_TENURE can "
        "be agreed to here; a down payment or the cheaper model needs the shop (ADR 0022). "
        "Needs the confirmed budget."
    ),
    response_description="The chosen plan and every alternative, in C6 order.",
    responses={
        200: {"content": {"application/json": {"example": PLAN_ALTERNATIVES_RESPONSE_EXAMPLE}}},
        **describe_customer_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            *SESSION_PROBLEMS,
            OFFER_NOT_QUOTED_PROBLEM,
            BUDGET_NOT_CONFIRMED_PROBLEM,
            CONSENT_ALREADY_GIVEN_PROBLEM,
            *QUOTING_PROBLEMS,
        ),
    },
)
def find_plan_alternatives(
    alternatives_request: PlanAlternativesRequest,
    credentials: CustomerSessionCredentialsDependency,
    plan_service: CustomerPlanServiceDependency,
) -> PlanAlternativesResponse:
    """Finds the alternatives to the chosen plan."""
    return PlanAlternativesResponse.from_advice(
        plan_service.suggest_alternatives(credentials, alternatives_request.offer_id)
    )
