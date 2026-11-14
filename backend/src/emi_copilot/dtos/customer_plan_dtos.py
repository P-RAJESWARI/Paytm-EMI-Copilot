"""Wire schemas of GET .../plans (C4): every quoted plan in order, none hidden."""

from typing import Annotated

from pydantic import Field

from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.ranking import PlanReasonCode
from emi_copilot.dtos.comfort_check_dtos import PlanComfortResponse
from emi_copilot.dtos.wire_types import (
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    PositiveAmountInPaise,
)
from emi_copilot.services.plan_advice_types import AdvisedPlan, PlanComparison


class CustomerPlanResponse(CamelCaseResponseModel):
    """One plan card: each month and extra in total side by side, budget fit and comfort.

    monthlyInstallmentInPaise is the lender's quoted figure; the other amounts are our exact
    schedule (ADR 0001). Budget fit uses the largest single installment (ADR 0020 decision 3).
    reasonCodes state facts only. comfort is null when the comfort check was skipped.
    """

    position: Annotated[int, Field(ge=1, examples=[1])]
    offer_id: Annotated[str, Field(examples=["mock-offer-cardless-12m"])]
    lender_label: Annotated[str, Field(examples=["Demo cardless lender (Mock)"])]
    emi_type: EmiType
    tenure_in_months: Annotated[int, Field(ge=1, examples=[12])]
    monthly_installment_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[205_000])]
    last_installment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[205_000])]
    extra_in_total_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[260_000])]
    total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_460_000])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    is_within_budget: Annotated[bool, Field(examples=[True])]
    amount_above_budget_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[0])]
    reason_codes: list[PlanReasonCode]
    comfort: PlanComfortResponse | None

    @classmethod
    def from_advised_plan(cls, advised_plan: AdvisedPlan) -> "CustomerPlanResponse":
        """Converts one ranked plan to integer paise and basis points."""
        ranked_plan = advised_plan.ranked_plan
        priced_offer = ranked_plan.priced_offer
        schedule = priced_offer.schedule
        return cls(
            position=ranked_plan.position,
            offer_id=priced_offer.offer.offer_id,
            lender_label=priced_offer.offer.lender_label,
            emi_type=priced_offer.offer.emi_type,
            tenure_in_months=priced_offer.offer.tenure_in_months,
            monthly_installment_in_paise=priced_offer.quoted_monthly_installment.to_paise(),
            last_installment_in_paise=schedule.last_installment.to_paise(),
            extra_in_total_in_paise=schedule.extra_in_total.to_paise(),
            total_payable_in_paise=schedule.total_payable.to_paise(),
            price_in_paise=schedule.principal.to_paise(),
            is_within_budget=ranked_plan.budget_fit.is_within_budget,
            amount_above_budget_in_paise=ranked_plan.budget_fit.amount_above_budget.to_paise(),
            reason_codes=list(ranked_plan.reason_codes),
            comfort=PlanComfortResponse.from_assessment(advised_plan.comfort),
        )


class CustomerPlansResponse(CamelCaseResponseModel):
    """Every plan for the budget; when none fits, all are still listed as above budget."""

    monthly_budget_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[300_000])]
    has_any_plan_within_budget: Annotated[bool, Field(examples=[True])]
    has_comfort_check: Annotated[bool, Field(examples=[True])]
    plans: list[CustomerPlanResponse]

    @classmethod
    def from_comparison(cls, comparison: PlanComparison) -> "CustomerPlansResponse":
        """Converts the comparison, keeping the ranked order."""
        return cls(
            monthly_budget_in_paise=comparison.ranking.monthly_budget.to_paise(),
            has_any_plan_within_budget=comparison.ranking.has_any_plan_within_budget,
            has_comfort_check=comparison.has_comfort_check,
            plans=[
                CustomerPlanResponse.from_advised_plan(plan) for plan in comparison.advised_plans
            ],
        )
