"""Tests for DownPaymentRule: derived, rounded up to ₹1,000, never the whole price."""

import pytest

from emi_copilot.domain.alternatives import DEFAULT_DOWN_PAYMENT_ROUNDING_STEP, DownPaymentRule
from emi_copilot.domain.errors import (
    InvalidEmiTermsError,
    InvalidMoneyAmountError,
    InvalidMonthlyBudgetError,
)
from emi_copilot.domain.money import Money


@pytest.mark.parametrize(
    ("price_in_rupees", "budget_in_rupees", "tenure_in_months", "expected_in_rupees"),
    [
        ("22000", "3000", 6, "4000"),
        ("22000", "1800", 6, "12000"),
        ("22000", "18000", 1, "4000"),
        ("22000", "17999.99", 1, "5000"),
        ("22000", "3667", 6, None),
        ("18000", "3000", 6, None),
        ("22000", "1", 1, None),
        ("22000", "1000", 1, "21000"),
        ("21500", "1", 1, None),
    ],
    ids=[
        "design-gap-4000",
        "no-fit-budget-gap-11200",
        "gap-exactly-one-step",
        "gap-one-paisa-over-a-step",
        "budget-covers-price",
        "budget-equals-price",
        "rounded-to-whole-price",
        "just-below-the-price",
        "rounded-above-the-price",
    ],
)
def test_suggest_down_payment_rounds_the_gap_up_to_the_next_step(
    price_in_rupees: str,
    budget_in_rupees: str,
    tenure_in_months: int,
    expected_in_rupees: str | None,
) -> None:
    """D = price - budget x tenure rounded up to ₹1,000; None if it fits or D reaches the price."""
    down_payment = DownPaymentRule().suggest_down_payment(
        Money.from_rupees(price_in_rupees), Money.from_rupees(budget_in_rupees), tenure_in_months
    )
    expected = None if expected_in_rupees is None else Money.from_rupees(expected_in_rupees)
    assert down_payment == expected


def test_suggest_down_payment_with_a_smaller_step_rounds_to_that_step() -> None:
    """The step is configuration: with ₹500 steps a ₹4,000.01 gap needs ₹4,500."""
    rule = DownPaymentRule(rounding_step=Money.from_rupees("500"))
    down_payment = rule.suggest_down_payment(
        Money.from_rupees("22000"), Money.from_rupees("17999.99"), 1
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


def test_suggest_down_payment_with_invalid_terms_or_budget_raises() -> None:
    """A zero price or tenure is invalid EMI terms; a zero budget is an invalid budget."""
    rule = DownPaymentRule()
    with pytest.raises(InvalidEmiTermsError):
        rule.suggest_down_payment(Money.from_paise(0), Money.from_rupees("3000"), 6)
    with pytest.raises(InvalidEmiTermsError):
        rule.suggest_down_payment(Money.from_rupees("22000"), Money.from_rupees("3000"), 0)
    with pytest.raises(InvalidMonthlyBudgetError):
        rule.suggest_down_payment(Money.from_rupees("22000"), Money.from_paise(0), 6)
