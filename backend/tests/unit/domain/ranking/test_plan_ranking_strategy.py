"""Tests for PlanRankingStrategy: C4 order, "no plan fits", tie-breaks and reason codes."""

import pytest

from emi_copilot.domain.errors import InvalidMonthlyBudgetError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.ranking import PlanRanking, PlanRankingStrategy, PlanReasonCode
from tests.plan_builders import (
    CARD_OFFER_ID,
    CARDLESS_OFFER_ID,
    NO_COST_OFFER_ID,
    build_cardless_plan_c,
    build_design_plans,
    build_priced_plan,
)

ZERO_RUPEES = Money.from_paise(0)
PRICE_OF_TWELVE_THOUSAND_RUPEES = Money.from_rupees("12000")


def rank_for_budget(priced_offers: list[PricedEmiOffer], budget_in_rupees: str) -> PlanRanking:
    """Ranks the plans for a monthly budget given in rupees."""
    return PlanRankingStrategy().rank(priced_offers, Money.from_rupees(budget_in_rupees))


def list_offer_ids(ranking: PlanRanking) -> list[str]:
    """Lists the offer ids in ranked order."""
    return [ranked_plan.priced_offer.offer.offer_id for ranked_plan in ranking.ranked_plans]


def test_rank_design_plans_on_three_thousand_budget_puts_the_fitting_plan_first() -> None:
    """C4: cardless fits; then no-cost (₹666.67 above) before card (₹850 above)."""
    ranking = rank_for_budget(list(build_design_plans()), "3000")

    assert list_offer_ids(ranking) == [CARDLESS_OFFER_ID, NO_COST_OFFER_ID, CARD_OFFER_ID]
    assert [plan.position for plan in ranking.ranked_plans] == [1, 2, 3]
    assert [plan.budget_fit.amount_above_budget.to_paise() for plan in ranking.ranked_plans] == [
        0,
        66_667,
        85_000,
    ]
    assert ranking.has_any_plan_within_budget
    assert ranking.monthly_budget == Money.from_rupees("3000")


def test_rank_design_plans_on_three_thousand_budget_gives_factual_reason_codes() -> None:
    """Cardless fits and is lowest monthly; no-cost has no extra; card is only above budget."""
    reason_codes_by_offer_id = {
        plan.priced_offer.offer.offer_id: plan.reason_codes
        for plan in rank_for_budget(list(build_design_plans()), "3000").ranked_plans
    }
    assert reason_codes_by_offer_id == {
        CARDLESS_OFFER_ID: (PlanReasonCode.WITHIN_BUDGET, PlanReasonCode.LOWEST_MONTHLY_AMOUNT),
        NO_COST_OFFER_ID: (
            PlanReasonCode.ABOVE_BUDGET,
            PlanReasonCode.NO_EXTRA_COST,
            PlanReasonCode.LOWEST_EXTRA_IN_TOTAL,
        ),
        CARD_OFFER_ID: (PlanReasonCode.ABOVE_BUDGET,),
    }


def test_rank_design_plans_when_no_plan_fits_still_lists_every_plan_above_budget() -> None:
    """₹1,800: none fits, all three stay listed with how far above the budget each is."""
    ranking = rank_for_budget(list(build_design_plans()), "1800")

    assert list_offer_ids(ranking) == [CARDLESS_OFFER_ID, NO_COST_OFFER_ID, CARD_OFFER_ID]
    assert [plan.budget_fit.amount_above_budget.to_paise() for plan in ranking.ranked_plans] == [
        25_000,
        186_667,
        205_000,
    ]
    assert not ranking.has_any_plan_within_budget
    assert all(PlanReasonCode.ABOVE_BUDGET in plan.reason_codes for plan in ranking.ranked_plans)


def test_rank_budget_exactly_equal_to_commitment_counts_as_within_budget() -> None:
    """A ₹2,050 budget fits plan C's ₹2,050.00 exactly."""
    ranked_plan = rank_for_budget([build_cardless_plan_c()], "2050").ranked_plans[0]
    assert ranked_plan.budget_fit.is_within_budget
    assert ranked_plan.monthly_commitment == Money.from_rupees("2050")
    assert PlanReasonCode.WITHIN_BUDGET in ranked_plan.reason_codes


@pytest.mark.parametrize("budget_in_rupees", ["1500", "2500"], ids=["above", "within"])
def test_rank_same_commitment_puts_smaller_extra_first(budget_in_rupees: str) -> None:
    """₹2,000 a month both ways: no-cost 6 months comes before 12 months with ₹12,000 extra."""
    costly_plan = build_priced_plan(
        "offer-costly-12m", 12, Money.from_rupees("12000"), PRICE_OF_TWELVE_THOUSAND_RUPEES
    )
    no_cost_plan = build_priced_plan(
        "offer-no-cost-6m", 6, ZERO_RUPEES, PRICE_OF_TWELVE_THOUSAND_RUPEES
    )
    ranking = rank_for_budget([costly_plan, no_cost_plan], budget_in_rupees)
    assert list_offer_ids(ranking) == ["offer-no-cost-6m", "offer-costly-12m"]
    assert all(
        PlanReasonCode.LOWEST_MONTHLY_AMOUNT in plan.reason_codes for plan in ranking.ranked_plans
    )


def test_rank_within_budget_same_extra_puts_shorter_tenure_first() -> None:
    """Both no-cost and both fit ₹3,000, so 6 months (₹2,000) precedes 12 months (₹1,000)."""
    longer_plan = build_priced_plan(
        "offer-no-cost-12m", 12, ZERO_RUPEES, PRICE_OF_TWELVE_THOUSAND_RUPEES
    )
    shorter_plan = build_priced_plan(
        "offer-no-cost-6m", 6, ZERO_RUPEES, PRICE_OF_TWELVE_THOUSAND_RUPEES
    )
    ranking = rank_for_budget([longer_plan, shorter_plan], "3000")
    assert list_offer_ids(ranking) == ["offer-no-cost-6m", "offer-no-cost-12m"]
    assert ranking.ranked_plans[1].reason_codes == (
        PlanReasonCode.WITHIN_BUDGET,
        PlanReasonCode.NO_EXTRA_COST,
        PlanReasonCode.LOWEST_MONTHLY_AMOUNT,
        PlanReasonCode.LOWEST_EXTRA_IN_TOTAL,
    )


def test_rank_identical_terms_are_ordered_by_offer_id() -> None:
    """Two plans with equal terms are ordered by offer id, so the order never depends on input."""
    second_plan = build_priced_plan("offer-b", 6, ZERO_RUPEES, PRICE_OF_TWELVE_THOUSAND_RUPEES)
    first_plan = build_priced_plan("offer-a", 6, ZERO_RUPEES, PRICE_OF_TWELVE_THOUSAND_RUPEES)
    assert list_offer_ids(rank_for_budget([second_plan, first_plan], "3000")) == [
        "offer-a",
        "offer-b",
    ]


def test_rank_no_plans_gives_an_empty_ranking_with_no_plan_within_budget() -> None:
    """With nothing quoted the ranking is empty and nothing fits."""
    ranking = rank_for_budget([], "3000")
    assert ranking.ranked_plans == ()
    assert not ranking.has_any_plan_within_budget


def test_rank_with_an_invalid_budget_raises_even_without_plans() -> None:
    """A zero budget is refused before any plan is looked at."""
    with pytest.raises(InvalidMonthlyBudgetError):
        PlanRankingStrategy().rank([], ZERO_RUPEES)


def test_plan_reason_code_has_no_recommendation_code() -> None:
    """Reason codes state facts only, in a fixed order (ADR 0020 decision 5)."""
    assert [code.value for code in PlanReasonCode] == [
        "WITHIN_BUDGET",
        "ABOVE_BUDGET",
        "NO_EXTRA_COST",
        "LOWEST_MONTHLY_AMOUNT",
        "LOWEST_EXTRA_IN_TOTAL",
    ]
