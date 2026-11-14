"""ChosenPlan: frozen as shown (the lender's monthly figure), stored as text and integer paise."""

from dataclasses import replace

import pytest

from emi_copilot.domain.errors import InvalidMoneyAmountError, InvalidSaleDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType, price_emi_offer
from emi_copilot.domain.sales import ChosenPlan
from tests.payment_builders import build_emi_offer
from tests.sale_builders import build_no_cost_chosen_plan, build_standard_chosen_plan

PLAN_B_DICTIONARY = {
    "offer_id": "offer-plan-b",
    "plan_kind": "STANDARD",
    "lender_label": "Your card's bank",
    "tenure_in_months": 6,
    "monthly_installment_in_paise": 385_000,
    "extra_in_total_in_paise": 110_000,
    "total_payable_in_paise": 2_310_000,
}


def test_from_priced_offer_keeps_the_lenders_monthly_figure_and_our_exact_totals() -> None:
    """Design plan B: ₹3,850 a month as quoted, ₹1,100 extra, ₹23,100 in total."""
    priced_offer = price_emi_offer(build_emi_offer(), Money.from_rupees("22000"))
    assert ChosenPlan.from_priced_offer(priced_offer) == build_standard_chosen_plan()


def test_from_priced_offer_on_a_mismatched_quote_keeps_the_quote_as_shown() -> None:
    """ADR 0001: when the lender's figure differs from our schedule, the lender's is shown."""
    mismatched_offer = build_emi_offer(quoted_monthly_installment=Money.from_rupees("4000"))
    priced_offer = price_emi_offer(mismatched_offer, Money.from_rupees("22000"))
    chosen_plan = ChosenPlan.from_priced_offer(priced_offer)
    assert chosen_plan.monthly_installment == Money.from_rupees("4000")
    assert chosen_plan.total_payable == Money.from_rupees("23100")


def test_price_is_the_total_minus_the_extra() -> None:
    """The plan remembers which price it was quoted on."""
    assert build_standard_chosen_plan().price == Money.from_rupees("22000")


@pytest.mark.parametrize("chosen_plan", [build_no_cost_chosen_plan(), build_standard_chosen_plan()])
def test_to_dictionary_round_trips_through_from_dictionary(chosen_plan: ChosenPlan) -> None:
    """The stored form decodes to an equal plan."""
    assert ChosenPlan.from_dictionary(chosen_plan.to_dictionary()) == chosen_plan


def test_to_dictionary_holds_text_and_integer_paise_only() -> None:
    """No float or Money object reaches the JSONB column."""
    assert build_standard_chosen_plan().to_dictionary() == PLAN_B_DICTIONARY


@pytest.mark.parametrize(
    "stored_plan",
    [
        {key: value for key, value in PLAN_B_DICTIONARY.items() if key != "offer_id"},
        {**PLAN_B_DICTIONARY, "card_number": "never"},
        {**PLAN_B_DICTIONARY, "tenure_in_months": True},
        {**PLAN_B_DICTIONARY, "monthly_installment_in_paise": 3850.0},
        {**PLAN_B_DICTIONARY, "offer_id": 7},
        {**PLAN_B_DICTIONARY, "plan_kind": "INTEREST_FREE"},
    ],
)
def test_from_dictionary_refuses_missing_extra_or_mistyped_fields(
    stored_plan: dict[str, object],
) -> None:
    """A stored plan is decoded exactly or not at all."""
    with pytest.raises(InvalidSaleDataError):
        ChosenPlan.from_dictionary(stored_plan)


def test_from_dictionary_with_negative_paise_raises() -> None:
    """Money refuses a negative stored amount."""
    with pytest.raises(InvalidMoneyAmountError):
        ChosenPlan.from_dictionary({**PLAN_B_DICTIONARY, "extra_in_total_in_paise": -1})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("offer_id", ""),
        ("lender_label", " "),
        ("plan_kind", "NO_COST"),
        ("tenure_in_months", 0),
        ("monthly_installment", Money.from_paise(0)),
        ("extra_in_total", Money.from_rupees("0.005")),
        ("total_payable", Money.from_paise(0)),
        ("extra_in_total", Money.from_rupees("23100")),
    ],
)
def test_chosen_plan_with_an_invalid_field_raises(field_name: str, value: object) -> None:
    """Labels, tenure and amounts are checked when the plan is frozen."""
    with pytest.raises(InvalidSaleDataError):
        replace(build_standard_chosen_plan(), **{field_name: value})  # type: ignore[arg-type]


def test_no_cost_chosen_plan_with_an_extra_raises() -> None:
    """A no-cost plan never costs anything extra."""
    with pytest.raises(InvalidSaleDataError, match="no-cost"):
        build_no_cost_chosen_plan(
            plan_kind=EmiType.NO_COST,
            extra_in_total=Money.from_rupees("1"),
            total_payable=Money.from_rupees("22001"),
        )
