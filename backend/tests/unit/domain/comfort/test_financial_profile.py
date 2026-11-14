"""Tests for FinancialProfile: a positive inflow and whole-paise existing EMIs."""

import pytest

from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.errors import InvalidComfortInputError
from emi_copilot.domain.money import Money


def test_financial_profile_with_no_existing_emis_is_valid() -> None:
    """A customer with no EMIs yet has existing EMIs of exactly zero."""
    profile = FinancialProfile(Money.from_rupees("30000"), Money.from_paise(0))
    assert profile.existing_emis_per_month.is_zero


@pytest.mark.parametrize(
    ("monthly_inflow", "existing_emis_per_month", "expected_message"),
    [
        (Money.from_paise(0), Money.from_rupees("8000"), "monthly inflow"),
        (Money.from_rupees("30000.001"), Money.from_rupees("8000"), "monthly inflow"),
        (30000, Money.from_rupees("8000"), "monthly inflow"),
        (Money.from_rupees("30000"), Money.from_rupees("8000.005"), "existing EMIs"),
        (Money.from_rupees("30000"), 8000, "existing EMIs"),
    ],
)
def test_financial_profile_with_invalid_amounts_raises(
    monthly_inflow: object, existing_emis_per_month: object, expected_message: str
) -> None:
    """Zero or sub-paise inflow, sub-paise EMIs and plain numbers are refused."""
    with pytest.raises(InvalidComfortInputError, match=expected_message):
        FinancialProfile(monthly_inflow, existing_emis_per_month)  # type: ignore[arg-type]
