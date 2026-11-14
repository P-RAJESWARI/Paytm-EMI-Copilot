"""M5 sales report: the funnel, missed sales, suggested actions and money due, per shop.

Every answer is an aggregate (rule 6): counts of 1 to 4 are suppressed (plan Q3), and no
customer's budget, step or progress is returned. Money is integer paise.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from emi_copilot.api.controllers.report_documentation import (
    FUNNEL_REPORT_EXAMPLE,
    MISSED_SALES_EXAMPLE,
    MONEY_DUE_EXAMPLE,
    SUGGESTED_ACTIONS_EXAMPLE,
)
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.openapi_documentation import (
    GATEWAY_FAILURE_PROBLEMS,
    GATEWAY_TIMEOUT_PROBLEM,
    MERCHANT_AUTHENTICATION_PROBLEM,
    MERCHANT_BEARER_NOTE,
    REQUEST_VALIDATION_PROBLEM,
    describe_problem_responses,
)
from emi_copilot.api.report_dependencies import (
    FunnelReportServiceDependency,
    MissedSalesReportServiceDependency,
    MoneyDueReportServiceDependency,
    SuggestedActionsServiceDependency,
)
from emi_copilot.dtos.money_due_dtos import MoneyDueResponse
from emi_copilot.dtos.report_dtos import (
    FunnelReportResponse,
    MissedSalesReportResponse,
    ReportRangeQuery,
)
from emi_copilot.dtos.suggested_action_dtos import SuggestedActionsResponse

report_router = APIRouter(tags=["reports"])

SUPPRESSION_NOTE = (
    "Only sales that are no longer CHOOSING are counted (READY_TO_PAY, PAID, "
    "PAYMENT_NOT_COMPLETED, EXPIRED), so a customer still at the counter shows in no report. "
    "A count from 1 to 4 is sent as customerCount null with isSuppressed true; 0 and 5 or more "
    "are shown, except a 0 right after a suppressed funnel stage, which is suppressed too. "
    "Periods are in IST; THIS_WEEK is Monday to Sunday. "
)
REPORT_PROBLEMS = (REQUEST_VALIDATION_PROBLEM, MERCHANT_AUTHENTICATION_PROBLEM)
GATEWAY_BACKED_REPORT_PROBLEMS = (
    *REPORT_PROBLEMS,
    *GATEWAY_FAILURE_PROBLEMS,
    GATEWAY_TIMEOUT_PROBLEM,
)


@report_router.get(
    "/reports/funnel",
    summary="Read where customers drop off",
    description=(
        "M5 funnel: the sales started in the period (a cohort), counted by every stage each "
        "reached: STARTED, BUDGET_TOLD, PLANS_VIEWED, AGREED, PAID. biggestDrop is the largest "
        "fall between adjacent stages (afterStage is the earlier one; ties go to the earliest), "
        "null when no stage falls. It is also null when it sits beside a suppressed stage, so "
        "neither the hidden count (by subtraction) nor where those few customers stopped (by "
        "its afterStage) can be worked out; between two shown stages a drop of 1 to 4 keeps "
        "its afterStage and is sent as customerCount null with isSuppressed true. "
        + SUPPRESSION_NOTE
        + MERCHANT_BEARER_NOTE
    ),
    response_description="The funnel.",
    responses={
        200: {"content": {"application/json": {"example": FUNNEL_REPORT_EXAMPLE}}},
        **describe_problem_responses(*REPORT_PROBLEMS),
    },
)
def get_funnel_report(
    report_range_query: Annotated[ReportRangeQuery, Query()],
    current_merchant: CurrentMerchant,
    funnel_report_service: FunnelReportServiceDependency,
) -> FunnelReportResponse:
    """Reads the signed-in shop's funnel for the range."""
    return FunnelReportResponse.from_view(
        funnel_report_service.get_funnel_report(
            current_merchant, report_range_query.reporting_range
        )
    )


@report_router.get(
    "/reports/missed-sales",
    summary="Read the missed sales and monthly budget ranges",
    description=(
        "M5 missed sales: sales started in the period that told a monthly amount below the "
        "cheapest no-extra-cost plan of their product and never agreed. budgetCeilingInPaise is "
        "the smallest range boundary (₹2,500, ₹3,000, ₹3,500, ₹4,000) at or above every missed "
        "amount, null when none was missed or one lies above ₹4,000. productInsight is the "
        "product with the most missed sales, with gateway-quoted figures. budgetBuckets counts "
        "every told amount per range (lower bound included); fewer than 5 tellers hide them all "
        "(areBudgetBucketsHidden). Figures derived from a suppressed missed count are left out: "
        "with missedCustomerCount suppressed, budgetCeilingInPaise and productInsight are null, "
        "no bucket isUnderCeiling and no bucket lists plans; with only the insight product's own "
        "count from 1 to 4, productInsight is null and no bucket lists plans. The gateway is "
        "asked for each product's plans. " + SUPPRESSION_NOTE + MERCHANT_BEARER_NOTE
    ),
    response_description="The missed-sales card.",
    responses={
        200: {"content": {"application/json": {"example": MISSED_SALES_EXAMPLE}}},
        **describe_problem_responses(*GATEWAY_BACKED_REPORT_PROBLEMS),
    },
)
def get_missed_sales_report(
    report_range_query: Annotated[ReportRangeQuery, Query()],
    current_merchant: CurrentMerchant,
    missed_sales_report_service: MissedSalesReportServiceDependency,
) -> MissedSalesReportResponse:
    """Reads the signed-in shop's missed-sales card for the range."""
    return MissedSalesReportResponse.from_view(
        missed_sales_report_service.get_missed_sales_report(
            current_merchant, report_range_query.reporting_range
        )
    )


@report_router.get(
    "/reports/suggested-actions",
    summary="Read what the shop can do to sell more",
    description=(
        "Deterministic suggestions as stable codes with paise parameters, never prose: "
        "ASK_BRAND_FOR_LONGER_NO_COST_PLAN (9 and 12-month no-cost installments on the "
        "insight product's price) and KEEP_CHEAPER_MODEL_READY (a cheaper model whose "
        "no-extra-cost monthly fits under the ceiling). Empty when nothing was missed, and "
        "while the missed count (or the insight product's own) is from 1 to 4. "
        + SUPPRESSION_NOTE
        + MERCHANT_BEARER_NOTE
    ),
    response_description="The actions, in a stable order.",
    responses={
        200: {"content": {"application/json": {"example": SUGGESTED_ACTIONS_EXAMPLE}}},
        **describe_problem_responses(*GATEWAY_BACKED_REPORT_PROBLEMS),
    },
)
def get_suggested_actions(
    report_range_query: Annotated[ReportRangeQuery, Query()],
    current_merchant: CurrentMerchant,
    suggested_actions_service: SuggestedActionsServiceDependency,
) -> SuggestedActionsResponse:
    """Reads the signed-in shop's suggested actions for the range."""
    return SuggestedActionsResponse.from_actions(
        suggested_actions_service.get_suggested_actions(
            current_merchant, report_range_query.reporting_range
        )
    )


@report_router.get(
    "/reports/money-due",
    summary="Read the money due from brands",
    description=(
        "M7: what brands are expected to pay the shop for no-cost EMI sales, in batches with "
        "estimated dates. Synthetic data from the labelled MockSettlementAdapter (rule 10); "
        "not filtered by any range (plan Q13). " + MERCHANT_BEARER_NOTE
    ),
    response_description="The batches, their total and the next expected date.",
    responses={
        200: {"content": {"application/json": {"example": MONEY_DUE_EXAMPLE}}},
        **describe_problem_responses(MERCHANT_AUTHENTICATION_PROBLEM),
    },
)
def get_money_due(
    current_merchant: CurrentMerchant, money_due_report_service: MoneyDueReportServiceDependency
) -> MoneyDueResponse:
    """Reads the signed-in shop's money due."""
    return MoneyDueResponse.from_report(money_due_report_service.get_money_due(current_merchant))
