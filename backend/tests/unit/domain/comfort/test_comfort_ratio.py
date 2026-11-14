"""Tests for ComfortRatio: exact ratio, one half-up rounding to basis points, refused inputs."""

import pytest

from emi_copilot.domain.comfort import ComfortRatio
from emi_copilot.domain.errors import InvalidComfortInputError
from emi_copilot.domain.money import Money


@pytest.mark.parametrize(
    ("monthly_commitment_in_rupees", "monthly_inflow_in_rupees", "expected_basis_points"),
    [
        ("8000", "30000", 2667),
        ("2050", "30000", 683),
        ("11666.67", "30000", 3889),
        ("11850", "30000", 3950),
        ("10050", "30000", 3350),
        ("11850", "20000", 5925),
        ("11000", "30000", 3667),
        ("1", "3", 3333),
        ("2", "3", 6667),
        ("0", "30000", 0),
        ("15000", "10000", 15000),
    ],
)
def test_comfort_ratio_in_basis_points_matches_hand_checked_values(
    monthly_commitment_in_rupees: str, monthly_inflow_in_rupees: str, expected_basis_points: int
) -> None:
    """Design ratios (A 38.89%, B 39.50%, C 33.50%, Risky 59.25%) and ratios above 100%."""
    ratio = ComfortRatio(
        Money.from_rupees(monthly_commitment_in_rupees), Money.from_rupees(monthly_inflow_in_rupees)
    )
    assert ratio.in_basis_points == expected_basis_points


@pytest.mark.parametrize(
    ("monthly_commitment_in_rupees", "expected_basis_points"),
    [
        ("3499.49", 3499),
        ("3499.50", 3500),
        ("1", 1),
        ("0.49", 0),
    ],
)
def test_comfort_ratio_in_basis_points_exact_half_rounds_up(
    monthly_commitment_in_rupees: str, expected_basis_points: int
) -> None:
    """On ₹10,000 one basis point is ₹1, so ₹0.50 is exactly half a basis point and rounds up."""
    ratio = ComfortRatio(
        Money.from_rupees(monthly_commitment_in_rupees), Money.from_rupees("10000")
    )
    assert ratio.in_basis_points == expected_basis_points


def test_comfort_ratio_in_basis_points_exact_half_on_odd_inflow_rounds_up() -> None:
    """₹1 on ₹20,000 is exactly 0.5 basis points, which rounds up to 1."""
    assert ComfortRatio(Money.from_rupees("1"), Money.from_rupees("20000")).in_basis_points == 1


def test_comfort_ratio_with_zero_inflow_raises() -> None:
    """A ratio of anything to nothing has no meaning, so it is refused."""
    with pytest.raises(InvalidComfortInputError, match="inflow"):
        ComfortRatio(Money.from_rupees("3850"), Money.from_paise(0))


@pytest.mark.parametrize(
    ("monthly_commitment", "monthly_inflow", "expected_message"),
    [
        (3850, Money.from_rupees("30000"), "commitment"),
        (Money.from_rupees("3850"), "30000", "inflow"),
    ],
)
def test_comfort_ratio_with_amounts_that_are_not_money_raises(
    monthly_commitment: object, monthly_inflow: object, expected_message: str
) -> None:
    """Only Money may become a ratio; plain numbers are refused."""
    with pytest.raises(InvalidComfortInputError, match=expected_message):
        ComfortRatio(monthly_commitment, monthly_inflow)  # type: ignore[arg-type]
