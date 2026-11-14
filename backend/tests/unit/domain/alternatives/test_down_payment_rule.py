"""Tests for DownPaymentRule: from the total payable, rounded up to ₹1,000, below the price."""

import pytest

from emi_copilot.domain.alternatives import DEFAULT_DOWN_PAYMENT_ROUNDING_STEP, DownPaymentRule
from emi_copilot.domain.errors import InvalidMoneyAmountError, InvalidMonthlyBudgetError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from tests.plan_builders import (
    CHEAPER_MODEL_PRICE,
    build_card_plan_b,
    build_no_cost_plan_a,
    build_priced_plan,
)

ZERO_RUPEES = Money.from_paise(0)


def build_one_month_plan(price_in_rupees: str, extra_in_rupees: str = "0") -> PricedEmiOffer:
    """Builds a one-month plan, so the gap is simply total payable minus one budget."""
    return build_priced_plan(
        "offer-one-month",
        1,
        Money.from_rupees(extra_in_rupees),
        Money.from_rupees(price_in_rupees),
    )


@pytest.mark.parametrize(
    ("chosen_plan", "budget_in_rupees", "expected_in_rupees"),
    [
        (build_no_cost_plan_a(), "3000", "4000"),
        (build_no_cost_plan_a(), "1800", "12000"),
        (build_card_plan_b(), "3700", "1000"),
        (build_one_month_plan("22000"), "18000", "4000"),
        (build_one_month_plan("22000"), "17999.99", "5000"),
        (build_one_month_plan("22000"), "1000", "21000"),
        (build_no_cost_plan_a(), "3667", None),
        (build_no_cost_plan_a(CHEAPER_MODEL_PRICE), "3000", None),
        (build_one_month_plan("22000"), "1", None),
        (build_one_month_plan("1000", "500"), "1", None),
    ],
    ids=[
        "design-plan-a-gap-4000",
        "no-fit-budget-gap-11200",
        "plan-b-extra-counts-gap-900",
        "gap-exactly-one-step",
        "gap-one-paisa-over-a-step",
        "just-below-the-price",
        "budget-covers-total",
        "budget-equals-total",
        "rounded-to-the-whole-price",
        "extra-pushes-it-above-the-price",
    ],
)
def test_suggest_down_payment_rounds_the_total_payable_gap_up_to_the_next_step(
    chosen_plan: PricedEmiOffer, budget_in_rupees: str, expected_in_rupees: str | None
) -> None:
    """D = total payable - budget x tenure, up to ₹1,000; None if it fits or D reaches the price."""
    down_payment = DownPaymentRule().suggest_down_payment(
        chosen_plan, Money.from_rupees(budget_in_rupees)
    )
    expected = None if expected_in_rupees is None else Money.from_rupees(expected_in_rupees)
    assert down_payment == expected


def test_suggest_down_payment_for_plan_b_counts_its_extra_cost() -> None:
    """Plan B (₹23,100 in total) above a ₹3,700 budget: price alone (₹22,000) would hide the gap."""
    plan_b = build_card_plan_b()
    assert Money.from_rupees("3700") * 6 >= plan_b.schedule.principal
    assert DownPaymentRule().suggest_down_payment(plan_b, Money.from_rupees("3700")) == (
        Money.from_rupees("1000")
    )


def test_suggest_down_payment_with_a_smaller_step_rounds_to_that_step() -> None:
    """The step is configuration: with ₹500 steps a ₹4,000.01 gap needs ₹4,500."""
    rule = DownPaymentRule(rounding_step=Money.from_rupees("500"))
    down_payment = rule.suggest_down_payment(
        build_one_month_plan("22000"), Money.from_rupees("17999.99")
    )
    assert down_payment == Money.from_rupees("4500")


def test_default_down_payment_rounding_step_is_one_thousand_rupees() -> None:
    """ADR 0020 decision 2: down payments are suggested in ₹1,000 steps."""
    assert Money.from_rupees("1000") == DEFAULT_DOWN_PAYMENT_ROUNDING_STEP


@pytest.mark.parametrize("rounding_step", [Money.from_paise(0), Money.from_rupees("0.001"), 1000])
def test_down_payment_rule_with_an_invalid_step_raises(rounding_step: object) -> None:
    """A zero, sub-paise or non-Money step is refused."""
    with pytest.raises(InvalidMoneyAmountError, match="rounding step"):
        DownPaymentRule(rounding_step)  # type: ignore[arg-type]


def test_suggest_down_payment_with_a_zero_budget_raises() -> None:
    """A zero budget is an invalid budget."""
    with pytest.raises(InvalidMonthlyBudgetError):
        DownPaymentRule().suggest_down_payment(build_no_cost_plan_a(), ZERO_RUPEES)
