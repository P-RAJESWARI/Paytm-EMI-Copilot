"""Tests for BudgetFit and monthly budget validation."""

import pytest

from emi_copilot.domain.errors import InvalidMonthlyBudgetError
from emi_copilot.domain.money import Money
from emi_copilot.domain.ranking import BudgetFit, require_valid_monthly_budget


@pytest.mark.parametrize(
    ("monthly_commitment_in_rupees", "expected_within", "expected_above_in_paise"),
    [
        ("2050.00", True, 0),
        ("3000.00", True, 0),
        ("3000.01", False, 1),
        ("3666.67", False, 66_667),
        ("3850.00", False, 85_000),
    ],
)
def test_budget_fit_against_three_thousand_rupees_gives_within_or_amount_above(
    monthly_commitment_in_rupees: str, *, expected_within: bool, expected_above_in_paise: int
) -> None:
    """Exactly the budget is within it; one paisa more is above it by one paisa."""
    budget_fit = BudgetFit(
        Money.from_rupees("3000"), Money.from_rupees(monthly_commitment_in_rupees)
    )
    assert budget_fit.is_within_budget is expected_within
    assert budget_fit.amount_above_budget.to_paise() == expected_above_in_paise


@pytest.mark.parametrize(
    "monthly_budget",
    [Money.from_paise(0), Money.from_rupees("3000.001"), 3000, "3000", None],
)
def test_require_valid_monthly_budget_with_invalid_budget_raises(monthly_budget: object) -> None:
    """A zero, sub-paise or non-Money budget is refused."""
    with pytest.raises(InvalidMonthlyBudgetError, match="monthly budget"):
        require_valid_monthly_budget(monthly_budget)


def test_budget_fit_with_a_commitment_that_is_not_money_raises() -> None:
    """The commitment must be Money too."""
    with pytest.raises(InvalidMonthlyBudgetError, match="commitment"):
        BudgetFit(Money.from_rupees("3000"), 2050)  # type: ignore[arg-type]


def test_invalid_monthly_budget_error_has_a_stable_code() -> None:
    """The API maps the error to problem+json by this code."""
    assert InvalidMonthlyBudgetError.code == "INVALID_MONTHLY_BUDGET"
