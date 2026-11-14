"""Tests for assess_comfort against the design's comfort figures (DESIGN_SPEC.md section 4)."""

import pytest

from emi_copilot.domain.comfort import (
    ComfortBand,
    ComfortBandClassificationStrategy,
    FinancialProfile,
    assess_comfort,
)
from emi_copilot.domain.errors import InvalidComfortInputError
from emi_copilot.domain.money import Money

STANDARD_PROFILE = FinancialProfile(Money.from_rupees("30000"), Money.from_rupees("8000"))
RISKY_PROFILE = FinancialProfile(Money.from_rupees("20000"), Money.from_rupees("8000"))


@pytest.mark.parametrize(
    ("profile", "plan_monthly_commitment_in_rupees", "expected_total_basis_points", "band"),
    [
        (STANDARD_PROFILE, "3666.67", 3889, ComfortBand.STRETCHING),
        (STANDARD_PROFILE, "3850.00", 3950, ComfortBand.STRETCHING),
        (STANDARD_PROFILE, "2050.00", 3350, ComfortBand.COMFORTABLE),
        (RISKY_PROFILE, "3850.00", 5925, ComfortBand.RISKY),
        (STANDARD_PROFILE, "3000.00", 3667, ComfortBand.STRETCHING),
    ],
    ids=["plan-a", "plan-b", "plan-c", "risky-plan-b", "down-payment-or-cheaper-model"],
)
def test_assess_comfort_design_plans_give_the_design_ratios_and_bands(
    profile: FinancialProfile,
    plan_monthly_commitment_in_rupees: str,
    expected_total_basis_points: int,
    band: ComfortBand,
) -> None:
    """A 38.89%, B 39.50%, C 33.50%, Risky 59.25% and the ₹3,000 alternatives 36.67% (ADR 0020)."""
    assessment = assess_comfort(
        profile,
        Money.from_rupees(plan_monthly_commitment_in_rupees),
        ComfortBandClassificationStrategy(),
    )
    assert assessment.total_ratio.in_basis_points == expected_total_basis_points
    assert assessment.band is band


def test_assess_comfort_plan_c_splits_into_existing_and_plan_parts() -> None:
    """C5 shows current EMIs 26.67% and this plan 6.83%, which together make 33.50%."""
    assessment = assess_comfort(
        STANDARD_PROFILE, Money.from_rupees("2050"), ComfortBandClassificationStrategy()
    )
    assert assessment.existing_emis_ratio.in_basis_points == 2667
    assert assessment.plan_ratio.in_basis_points == 683
    assert assessment.total_ratio.in_basis_points == 3350


def test_assess_comfort_total_comes_from_the_exact_sum_not_the_rounded_parts() -> None:
    """Parts 0.4 and 0.4 basis points each round to 0, but together 0.8 rounds to 1."""
    profile = FinancialProfile(Money.from_rupees("10000"), Money.from_rupees("0.40"))
    assessment = assess_comfort(
        profile, Money.from_rupees("0.40"), ComfortBandClassificationStrategy()
    )
    assert assessment.existing_emis_ratio.in_basis_points == 0
    assert assessment.plan_ratio.in_basis_points == 0
    assert assessment.total_ratio.in_basis_points == 1


def test_assess_comfort_with_a_commitment_that_is_not_money_raises() -> None:
    """The plan's monthly commitment must be Money, never a plain number."""
    with pytest.raises(InvalidComfortInputError, match="commitment"):
        assess_comfort(STANDARD_PROFILE, 3850, ComfortBandClassificationStrategy())  # type: ignore[arg-type]
