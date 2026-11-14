"""Property-based tests for PlanRankingStrategy over generated plan lists.

Ranges: price ₹1,000 to ₹10,00,000, up to 6 plans with unique ids, tenures 3 to 24 months, an
extra of 0% to 30% of the price, a lender quote within ₹1 of the engine, and a budget from one
paisa up to the price.
"""

from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.ranking import PlanRanking, PlanRankingStrategy
from tests.plan_builders import build_priced_plan

TENURE_IN_MONTHS = st.sampled_from([3, 6, 9, 12, 18, 24])
QUOTE_DIFFERENCE_IN_PAISE = st.integers(min_value=-100, max_value=100)


@st.composite
def plan_lists(draw: st.DrawFn) -> tuple[list[PricedEmiOffer], Money]:
    """Draws up to six priced plans on one price, with unique offer ids, and a monthly budget."""
    price_in_paise = draw(st.integers(min_value=100_000, max_value=100_000_000))
    price = Money.from_paise(price_in_paise)
    plan_count = draw(st.integers(min_value=0, max_value=6))
    priced_offers = []
    for plan_number in range(plan_count):
        extra_in_paise = draw(st.integers(min_value=0, max_value=price_in_paise * 3 // 10))
        plan = build_priced_plan(
            f"offer-{plan_number}", draw(TENURE_IN_MONTHS), Money.from_paise(extra_in_paise), price
        )
        quoted_in_paise = plan.quoted_monthly_installment.to_paise()
        adjusted_quote_in_paise = max(1, quoted_in_paise + draw(QUOTE_DIFFERENCE_IN_PAISE))
        priced_offers.append(
            build_priced_plan(
                plan.offer.offer_id,
                plan.offer.tenure_in_months,
                Money.from_paise(extra_in_paise),
                price,
                quoted_monthly_installment=Money.from_paise(adjusted_quote_in_paise),
            )
        )
    budget_in_paise = draw(st.integers(min_value=1, max_value=price_in_paise))
    return priced_offers, Money.from_paise(budget_in_paise)


def list_offer_ids(ranking: PlanRanking) -> list[str]:
    """Lists the offer ids in ranked order."""
    return [ranked_plan.priced_offer.offer.offer_id for ranked_plan in ranking.ranked_plans]


@given(plans_and_budget=plan_lists())
def test_rank_any_plans_keeps_every_plan_exactly_once(
    plans_and_budget: tuple[list[PricedEmiOffer], Money],
) -> None:
    """The ranking is a permutation of the input: no plan is dropped or repeated."""
    priced_offers, monthly_budget = plans_and_budget
    ranking = PlanRankingStrategy().rank(priced_offers, monthly_budget)
    assert sorted(list_offer_ids(ranking)) == sorted(plan.offer.offer_id for plan in priced_offers)
    assert [plan.position for plan in ranking.ranked_plans] == list(
        range(1, len(priced_offers) + 1)
    )


@given(plans_and_budget=plan_lists(), data=st.data())
def test_rank_any_plans_order_does_not_depend_on_input_order(
    plans_and_budget: tuple[list[PricedEmiOffer], Money], data: st.DataObject
) -> None:
    """Shuffling the input or ranking twice gives the same ranking."""
    priced_offers, monthly_budget = plans_and_budget
    shuffled_offers = data.draw(st.permutations(priced_offers))
    strategy = PlanRankingStrategy()
    first_ranking = strategy.rank(priced_offers, monthly_budget)
    assert strategy.rank(shuffled_offers, monthly_budget) == first_ranking
    assert strategy.rank(priced_offers, monthly_budget) == first_ranking


@given(plans_and_budget=plan_lists())
def test_rank_any_plans_lists_fitting_plans_before_the_others(
    plans_and_budget: tuple[list[PricedEmiOffer], Money],
) -> None:
    """Every plan within the budget precedes every plan above it."""
    priced_offers, monthly_budget = plans_and_budget
    ranking = PlanRankingStrategy().rank(priced_offers, monthly_budget)
    within_flags = [plan.budget_fit.is_within_budget for plan in ranking.ranked_plans]
    assert within_flags == sorted(within_flags, reverse=True)
    assert ranking.has_any_plan_within_budget is any(within_flags)
