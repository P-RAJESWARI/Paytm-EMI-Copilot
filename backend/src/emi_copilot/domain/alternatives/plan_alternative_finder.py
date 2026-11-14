"""PlanAlternativeFinder: down payment, longer tenure and cheaper model, engine-recomputed."""

from collections.abc import Sequence

from emi_copilot.domain.alternatives.cheaper_model_quote import CheaperModelQuote
from emi_copilot.domain.alternatives.plan_alternative import PlanAlternative, PlanAlternatives
from emi_copilot.domain.errors import InvalidEmiTermsError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.payments.field_validation import require_positive_whole_paise_money
from emi_copilot.domain.ranking import (
    PlanRankingStrategy,
    calculate_monthly_commitment,
    require_valid_monthly_budget,
)


def _find_offer_by_id(
    priced_offers: Sequence[PricedEmiOffer], offer_id: str
) -> PricedEmiOffer | None:
    """Gives the first plan with the offer id, or None when it is not quoted."""
    return next((offer for offer in priced_offers if offer.offer.offer_id == offer_id), None)


def _pick_cheaper_model_offer(
    cheaper_model: CheaperModelQuote, chosen_offer_id: str
) -> PricedEmiOffer:
    """Gives the cheaper model's plan with the chosen offer id, else its lowest monthly plan."""
    same_offer = _find_offer_by_id(cheaper_model.priced_offers, chosen_offer_id)
    if same_offer is not None:
        return same_offer
    return min(
        cheaper_model.priced_offers,
        key=lambda offer: (calculate_monthly_commitment(offer), offer.offer.offer_id),
    )


class PlanAlternativeFinder:
    """Finds every C6 alternative to the chosen plan; none is hidden, even if it costs more.

    Order: the down payment, then longer tenures in ranking order, then cheaper models in the order
    given. Every figure comes from plans priced by the EMI engine (ADR 0020 decisions 1 and 2).
    """

    def __init__(self, ranking_strategy: PlanRankingStrategy | None = None) -> None:
        """Stores the ranking used to order longer-tenure plans; the C4 ranking by default."""
        self._ranking_strategy = ranking_strategy or PlanRankingStrategy()

    def find_alternatives(  # noqa: PLR0913 - one named input per C6 alternative source
        self,
        chosen_plan: PricedEmiOffer,
        *,
        item_offers: Sequence[PricedEmiOffer],
        monthly_budget: Money,
        down_payment: Money | None,
        down_payment_offers: Sequence[PricedEmiOffer],
        cheaper_models: Sequence[CheaperModelQuote],
    ) -> PlanAlternatives:
        """Gives the chosen plan with its down-payment, longer-tenure and cheaper-model options."""
        require_valid_monthly_budget(monthly_budget)
        previous_monthly_commitment = calculate_monthly_commitment(chosen_plan)
        alternatives = (
            *self._find_down_payment_alternatives(
                chosen_plan,
                down_payment,
                down_payment_offers,
                previous_monthly_commitment,
                monthly_budget,
            ),
            *self._find_longer_tenure_alternatives(
                chosen_plan, item_offers, previous_monthly_commitment, monthly_budget
            ),
            *self._find_cheaper_model_alternatives(
                chosen_plan, cheaper_models, previous_monthly_commitment, monthly_budget
            ),
        )
        return PlanAlternatives(chosen_plan=chosen_plan, alternatives=alternatives)

    def _find_down_payment_alternatives(
        self,
        chosen_plan: PricedEmiOffer,
        down_payment: Money | None,
        down_payment_offers: Sequence[PricedEmiOffer],
        previous_monthly_commitment: Money,
        monthly_budget: Money,
    ) -> tuple[PlanAlternative, ...]:
        """Gives the chosen offer re-quoted on the price less the down payment, if it is quoted."""
        if down_payment is None:
            return ()
        require_positive_whole_paise_money(down_payment, "down payment", InvalidEmiTermsError)
        reduced_plan = _find_offer_by_id(down_payment_offers, chosen_plan.offer.offer_id)
        if reduced_plan is None:
            return ()
        if reduced_plan.schedule.principal + down_payment != chosen_plan.schedule.principal:
            raise InvalidEmiTermsError(
                "The down-payment plan must be priced on the price less the down payment."
            )
        return (
            PlanAlternative.for_down_payment(
                reduced_plan, down_payment, previous_monthly_commitment, monthly_budget
            ),
        )

    def _find_longer_tenure_alternatives(
        self,
        chosen_plan: PricedEmiOffer,
        item_offers: Sequence[PricedEmiOffer],
        previous_monthly_commitment: Money,
        monthly_budget: Money,
    ) -> tuple[PlanAlternative, ...]:
        """Gives every plan for the item that runs longer than the chosen one, in ranking order."""
        chosen_tenure_in_months = chosen_plan.offer.tenure_in_months
        longer_plans = [
            offer for offer in item_offers if offer.offer.tenure_in_months > chosen_tenure_in_months
        ]
        ranking = self._ranking_strategy.rank(longer_plans, monthly_budget)
        return tuple(
            PlanAlternative.for_longer_tenure(
                ranked_plan.priced_offer, previous_monthly_commitment, monthly_budget
            )
            for ranked_plan in ranking.ranked_plans
        )

    def _find_cheaper_model_alternatives(
        self,
        chosen_plan: PricedEmiOffer,
        cheaper_models: Sequence[CheaperModelQuote],
        previous_monthly_commitment: Money,
        monthly_budget: Money,
    ) -> tuple[PlanAlternative, ...]:
        """Gives one plan per model priced below the chosen item that has any plan quoted."""
        chosen_price = chosen_plan.schedule.principal
        return tuple(
            PlanAlternative.for_cheaper_model(
                _pick_cheaper_model_offer(cheaper_model, chosen_plan.offer.offer_id),
                cheaper_model,
                previous_monthly_commitment,
                monthly_budget,
            )
            for cheaper_model in cheaper_models
            if cheaper_model.price < chosen_price and cheaper_model.priced_offers
        )
