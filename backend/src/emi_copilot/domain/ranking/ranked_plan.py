"""RankedPlan and PlanRanking: every quoted plan, in C4 order, with its budget fit and reasons."""

from dataclasses import dataclass

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.ranking.budget_fit import BudgetFit
from emi_copilot.domain.ranking.plan_reason_code import PlanReasonCode


@dataclass(frozen=True, slots=True)
class RankedPlan:
    """One plan at its 1-based position, with its budget fit and factual reason codes."""

    priced_offer: PricedEmiOffer
    position: int
    budget_fit: BudgetFit
    reason_codes: tuple[PlanReasonCode, ...]

    @property
    def monthly_commitment(self) -> Money:
        """Gives the monthly amount the plan was ranked and fitted on."""
        return self.budget_fit.monthly_commitment


@dataclass(frozen=True, slots=True)
class PlanRanking:
    """Every plan for the budget, in order; plans above the budget are listed, never dropped."""

    monthly_budget: Money
    ranked_plans: tuple[RankedPlan, ...]

    @property
    def has_any_plan_within_budget(self) -> bool:
        """Tells whether at least one plan fits; False is the C4 "no plan fits" state."""
        return any(ranked_plan.budget_fit.is_within_budget for ranked_plan in self.ranked_plans)
