"""Orders every quoted plan for a monthly budget and labels each with factual reason codes."""

from collections.abc import Sequence

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.ranking.budget_fit import BudgetFit, require_valid_monthly_budget
from emi_copilot.domain.ranking.monthly_commitment import calculate_monthly_commitment
from emi_copilot.domain.ranking.plan_reason_code import PlanReasonCode
from emi_copilot.domain.ranking.ranked_plan import PlanRanking, RankedPlan

_RankingKey = tuple[Money, Money, int, str]


def _calculate_ranking_key(priced_offer: PricedEmiOffer, budget_fit: BudgetFit) -> _RankingKey:
    """Gives amount above budget, extra in total, tenure and offer id, compared in that order."""
    return (
        budget_fit.amount_above_budget,
        priced_offer.schedule.extra_in_total,
        priced_offer.offer.tenure_in_months,
        priced_offer.offer.offer_id,
    )


# Pattern: Strategy. The C4 ordering rule is one swappable, unit-tested class; a single concrete
# rule today, so no abstract base until a second ordering is needed (design-patterns.md section 3).
class PlanRankingStrategy:
    """Ranks plans within the budget first, then by how far above it (ADR 0020 decision 5).

    Ties go to the smaller extra in total, then the shorter tenure, then the offer id, so the
    order is total and deterministic. Every plan is kept, however far above the budget it is.
    """

    def rank(self, priced_offers: Sequence[PricedEmiOffer], monthly_budget: Money) -> PlanRanking:
        """Orders the plans for the budget and gives each its position and reason codes."""
        require_valid_monthly_budget(monthly_budget)
        fitted_offers = [
            (priced_offer, BudgetFit(monthly_budget, calculate_monthly_commitment(priced_offer)))
            for priced_offer in priced_offers
        ]
        fitted_offers.sort(key=lambda fitted: _calculate_ranking_key(*fitted))
        lowest_monthly_commitment = min(
            (budget_fit.monthly_commitment for _, budget_fit in fitted_offers), default=None
        )
        lowest_extra_in_total = min(
            (priced_offer.schedule.extra_in_total for priced_offer, _ in fitted_offers),
            default=None,
        )
        ranked_plans = tuple(
            RankedPlan(
                priced_offer=priced_offer,
                position=position,
                budget_fit=budget_fit,
                reason_codes=_find_reason_codes(
                    priced_offer, budget_fit, lowest_monthly_commitment, lowest_extra_in_total
                ),
            )
            for position, (priced_offer, budget_fit) in enumerate(fitted_offers, start=1)
        )
        return PlanRanking(monthly_budget=monthly_budget, ranked_plans=ranked_plans)


def _find_reason_codes(
    priced_offer: PricedEmiOffer,
    budget_fit: BudgetFit,
    lowest_monthly_commitment: Money | None,
    lowest_extra_in_total: Money | None,
) -> tuple[PlanReasonCode, ...]:
    """Lists the facts that hold for one plan, in PlanReasonCode declaration order."""
    extra_in_total = priced_offer.schedule.extra_in_total
    facts_by_code = {
        PlanReasonCode.WITHIN_BUDGET: budget_fit.is_within_budget,
        PlanReasonCode.ABOVE_BUDGET: not budget_fit.is_within_budget,
        PlanReasonCode.NO_EXTRA_COST: extra_in_total.is_zero,
        PlanReasonCode.LOWEST_MONTHLY_AMOUNT: (
            budget_fit.monthly_commitment == lowest_monthly_commitment
        ),
        PlanReasonCode.LOWEST_EXTRA_IN_TOTAL: extra_in_total == lowest_extra_in_total,
    }
    return tuple(code for code in PlanReasonCode if facts_by_code[code])
