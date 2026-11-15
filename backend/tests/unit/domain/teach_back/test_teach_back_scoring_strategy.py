"""TeachBackScoringStrategy: the tenure exactly and the monthly within 5%, or try again."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.domain.ai_errors import InvalidTeachBackInputError
from emi_copilot.domain.teach_back import (
    DEMO_TEACH_BACK_TOLERANCE,
    TeachBackResult,
    TeachBackScoringStrategy,
    TeachBackTolerance,
)

CLOSE_ENOUGH, TRY_AGAIN = TeachBackResult.CLOSE_ENOUGH, TeachBackResult.TRY_AGAIN
MONTHLY_IN_RUPEES = 4_000
TENURE_IN_MONTHS = 6


def score(*stated_numbers: int) -> TeachBackResult:
    """Scores numbers against a ₹4,000 a month, 6-month plan (5% is exactly ₹200)."""
    return TeachBackScoringStrategy().score(stated_numbers, MONTHLY_IN_RUPEES, TENURE_IN_MONTHS)


@pytest.mark.parametrize(
    ("stated_numbers", "expected_result"),
    [
        ((4_000, 6), CLOSE_ENOUGH),
        ((6, 4_000), CLOSE_ENOUGH),
        ((4_200, 6), CLOSE_ENOUGH),
        ((3_800, 6), CLOSE_ENOUGH),
        ((4_201, 6), TRY_AGAIN),
        ((3_799, 6), TRY_AGAIN),
        ((4_000, 7), TRY_AGAIN),
        ((4_000,), TRY_AGAIN),
        ((6,), TRY_AGAIN),
        ((), TRY_AGAIN),
        ((6, 6), TRY_AGAIN),
        ((12, 4_000, 6), CLOSE_ENOUGH),
    ],
)
def test_teach_back_scoring_boundaries(
    stated_numbers: tuple[int, ...], expected_result: TeachBackResult
) -> None:
    """Exactly 5% away passes, a rupee more fails; a wrong or missing tenure fails."""
    assert score(*stated_numbers) is expected_result


def test_teach_back_scoring_design_plan_a_accepts_rounded_speech() -> None:
    """₹3,667 a month: "3,700 for 6 months" is close enough, "3,000" is not."""
    strategy = TeachBackScoringStrategy()
    assert strategy.score((3_700, 6), 3_667, 6) is CLOSE_ENOUGH
    assert strategy.score((3_000, 6), 3_667, 6) is TRY_AGAIN


@given(
    monthly_in_rupees=st.integers(min_value=100, max_value=1_000_000),
    offset_in_basis_points=st.integers(min_value=-1_000, max_value=1_000),
)
def test_teach_back_scoring_matches_the_exact_decimal_rule(
    monthly_in_rupees: int, offset_in_basis_points: int
) -> None:
    """CLOSE_ENOUGH exactly when |stated - monthly| <= 5% of monthly, in exact Decimal maths."""
    stated = monthly_in_rupees + monthly_in_rupees * offset_in_basis_points // 10_000
    is_within = abs(Decimal(stated - monthly_in_rupees)) <= Decimal(monthly_in_rupees) * Decimal(
        "0.05"
    )
    expected = CLOSE_ENOUGH if is_within else TRY_AGAIN
    assert TeachBackScoringStrategy().score((stated, 60), monthly_in_rupees, 60) is expected


def test_teach_back_tolerance_of_zero_needs_the_exact_amount() -> None:
    """The tolerance is configurable; zero means the exact monthly figure."""
    strategy = TeachBackScoringStrategy(TeachBackTolerance(Decimal(0)))
    assert strategy.score((4_000, 6), 4_000, 6) is CLOSE_ENOUGH
    assert strategy.score((4_001, 6), 4_000, 6) is TRY_AGAIN


@pytest.mark.parametrize("share", [Decimal("-0.01"), Decimal(1), 0.05])
def test_teach_back_tolerance_outside_zero_to_one_or_a_float_is_rejected(share: object) -> None:
    """A share must be an exact Decimal from 0 up to 1."""
    with pytest.raises(InvalidTeachBackInputError):
        TeachBackTolerance(share)  # type: ignore[arg-type]


def test_demo_teach_back_tolerance_is_five_percent() -> None:
    """Plan Q7's heuristic, held in one value object."""
    assert DEMO_TEACH_BACK_TOLERANCE.monthly_amount_share == Decimal("0.05")
