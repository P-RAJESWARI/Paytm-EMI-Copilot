"""Property-based tests for PlanAlternativeFinder over generated plan lists."""

from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.domain.alternatives import AlternativeKind, PlanAlternativeFinder
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from tests.unit.domain.ranking.test_plan_ranking_properties import plan_lists


@given(plans_and_budget=plan_lists(), data=st.data())
def test_find_alternatives_longer_tenure_never_includes_the_chosen_plan(
    plans_and_budget: tuple[list[PricedEmiOffer], Money], data: st.DataObject
) -> None:
    """Every longer-tenure option runs longer than the chosen plan, so it is never the plan itself.

    Every item plan that runs longer is offered exactly once, and finding twice gives equal results.
    """
    priced_offers, monthly_budget = plans_and_budget
    if not priced_offers:
        return
    chosen_plan = data.draw(st.sampled_from(priced_offers))
    finder = PlanAlternativeFinder()

    def find() -> tuple[str, ...]:
        """Finds the longer-tenure options and lists their offer ids."""
        plan_alternatives = finder.find_alternatives(
            chosen_plan,
            item_offers=priced_offers,
            monthly_budget=monthly_budget,
            down_payment=None,
            down_payment_offers=(),
            cheaper_models=(),
        )
        assert all(
            alternative.kind is AlternativeKind.LONGER_TENURE
            and alternative.priced_offer.offer.tenure_in_months > chosen_plan.offer.tenure_in_months
            for alternative in plan_alternatives.alternatives
        )
        return tuple(
            alternative.priced_offer.offer.offer_id
            for alternative in plan_alternatives.alternatives
        )

    longer_offer_ids = find()
    assert chosen_plan.offer.offer_id not in longer_offer_ids
    assert sorted(longer_offer_ids) == sorted(
        offer.offer.offer_id
        for offer in priced_offers
        if offer.offer.tenure_in_months > chosen_plan.offer.tenure_in_months
    )
    assert find() == longer_offer_ids
