"""PlanAdviceService: ranks the quoted plans, checks comfort and finds smarter alternatives."""

from collections.abc import Sequence
from dataclasses import replace

from emi_copilot.domain.alternatives import (
    CheaperModelQuote,
    DownPaymentRule,
    PlanAlternativeFinder,
)
from emi_copilot.domain.comfort import (
    ComfortAssessment,
    ComfortBandClassificationStrategy,
    FinancialProfile,
    assess_comfort,
)
from emi_copilot.domain.errors import OfferNotFoundError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery, PricedEmiOffer
from emi_copilot.domain.ranking import (
    BudgetFit,
    PlanRankingStrategy,
    calculate_monthly_commitment,
    require_valid_monthly_budget,
)
from emi_copilot.services.plan_advice_types import (
    AdvisedAlternative,
    AdvisedPlan,
    AlternativesAdvice,
    CheaperModelCandidate,
    PlanComparison,
    PricedOfferSource,
)


class PlanAdviceService:
    """Turns the quoted plans into C4's comparison and C6's alternatives; AI plays no part.

    Every figure comes from the EMI engine and the comfort engine. The comfort assessment is
    attached only when the customer consented to the comfort check (a profile is given).
    """

    def __init__(
        self,
        offer_source: PricedOfferSource,
        ranking_strategy: PlanRankingStrategy | None = None,
        classification_strategy: ComfortBandClassificationStrategy | None = None,
        alternative_finder: PlanAlternativeFinder | None = None,
        down_payment_rule: DownPaymentRule | None = None,
    ) -> None:
        """Keeps the offer source and the rules; each rule defaults to its ADR 0020 form."""
        self._offer_source = offer_source
        self._ranking_strategy = ranking_strategy or PlanRankingStrategy()
        self._classification_strategy = (
            classification_strategy or ComfortBandClassificationStrategy()
        )
        self._alternative_finder = alternative_finder or PlanAlternativeFinder(
            self._ranking_strategy
        )
        self._down_payment_rule = down_payment_rule or DownPaymentRule()

    def compare_plans(
        self,
        item: OfferDiscoveryQuery,
        monthly_budget: Money,
        financial_profile: FinancialProfile | None,
    ) -> PlanComparison:
        """Ranks every plan quoted for the item and assesses comfort when a profile is given."""
        require_valid_monthly_budget(monthly_budget)
        ranking = self._ranking_strategy.rank(
            self._offer_source.discover_offers(item), monthly_budget
        )
        advised_plans = tuple(
            AdvisedPlan(
                ranked_plan=ranked_plan,
                comfort=self._assess(financial_profile, ranked_plan.monthly_commitment),
            )
            for ranked_plan in ranking.ranked_plans
        )
        return PlanComparison(
            ranking=ranking,
            advised_plans=advised_plans,
            has_comfort_check=financial_profile is not None,
        )

    def suggest_alternatives(
        self,
        item: OfferDiscoveryQuery,
        chosen_offer_id: str,
        monthly_budget: Money,
        financial_profile: FinancialProfile | None,
        cheaper_models: Sequence[CheaperModelCandidate],
    ) -> AlternativesAdvice:
        """Finds C6's down payment, longer tenure and cheaper model options for the chosen plan.

        Raises OfferNotFoundError when the chosen offer is not quoted for the item.
        """
        require_valid_monthly_budget(monthly_budget)
        item_offers = self._offer_source.discover_offers(item)
        chosen_plan = _find_chosen_plan(item_offers, chosen_offer_id)
        down_payment = self._down_payment_rule.suggest_down_payment(chosen_plan, monthly_budget)
        plan_alternatives = self._alternative_finder.find_alternatives(
            chosen_plan,
            item_offers=item_offers,
            monthly_budget=monthly_budget,
            down_payment=down_payment,
            down_payment_offers=self._quote_after_down_payment(item, down_payment),
            cheaper_models=self._quote_cheaper_models(item, cheaper_models),
        )
        advised_alternatives = tuple(
            AdvisedAlternative(
                alternative=alternative,
                comfort=self._assess(financial_profile, alternative.monthly_commitment),
            )
            for alternative in plan_alternatives.alternatives
        )
        chosen_commitment = calculate_monthly_commitment(chosen_plan)
        return AlternativesAdvice(
            chosen_plan=chosen_plan,
            chosen_plan_budget_fit=BudgetFit(monthly_budget, chosen_commitment),
            chosen_plan_comfort=self._assess(financial_profile, chosen_commitment),
            advised_alternatives=advised_alternatives,
            has_lower_monthly_alternative=plan_alternatives.has_lower_monthly_alternative,
        )

    def _quote_after_down_payment(
        self, item: OfferDiscoveryQuery, down_payment: Money | None
    ) -> tuple[PricedEmiOffer, ...]:
        """Re-quotes the same item at the price less the down payment; nothing without one."""
        if down_payment is None:
            return ()
        return self._offer_source.discover_offers(replace(item, price=item.price - down_payment))

    def _quote_cheaper_models(
        self, item: OfferDiscoveryQuery, cheaper_models: Sequence[CheaperModelCandidate]
    ) -> tuple[CheaperModelQuote, ...]:
        """Quotes every candidate priced below the item; dearer candidates are not asked for."""
        return tuple(
            CheaperModelQuote(
                product_id=candidate.product_id,
                product_name=candidate.product_name,
                price=candidate.price,
                priced_offers=self._offer_source.discover_offers(
                    candidate.to_offer_discovery_query()
                ),
            )
            for candidate in cheaper_models
            if candidate.price < item.price
        )

    def _assess(
        self, financial_profile: FinancialProfile | None, monthly_commitment: Money
    ) -> ComfortAssessment | None:
        """Assesses comfort for one monthly commitment, or gives None without a profile."""
        if financial_profile is None:
            return None
        return assess_comfort(financial_profile, monthly_commitment, self._classification_strategy)


def _find_chosen_plan(
    item_offers: Sequence[PricedEmiOffer], chosen_offer_id: str
) -> PricedEmiOffer:
    """Gives the quoted plan with the chosen offer id; raises OfferNotFoundError otherwise."""
    for priced_offer in item_offers:
        if priced_offer.offer.offer_id == chosen_offer_id:
            return priced_offer
    raise OfferNotFoundError("The chosen offer is not quoted for this item and price.")
