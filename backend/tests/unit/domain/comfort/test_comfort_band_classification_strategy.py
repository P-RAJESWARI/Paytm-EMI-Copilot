"""Tests for ComfortBandClassificationStrategy: band boundaries on the rounded basis points."""

import pytest

from emi_copilot.domain.comfort import (
    DEMO_COMFORT_THRESHOLDS,
    ComfortBand,
    ComfortBandClassificationStrategy,
    ComfortRatio,
    ComfortThresholds,
)
from emi_copilot.domain.money import Money

INFLOW_OF_TEN_THOUSAND_RUPEES = Money.from_rupees("10000")


@pytest.mark.parametrize(
    ("monthly_commitment_in_rupees", "expected_basis_points", "expected_band"),
    [
        ("3499.49", 3499, ComfortBand.COMFORTABLE),
        ("3499.50", 3500, ComfortBand.STRETCHING),
        ("3500.00", 3500, ComfortBand.STRETCHING),
        ("5000.00", 5000, ComfortBand.STRETCHING),
        ("5000.49", 5000, ComfortBand.STRETCHING),
        ("5000.50", 5001, ComfortBand.RISKY),
        ("0", 0, ComfortBand.COMFORTABLE),
        ("12000", 12000, ComfortBand.RISKY),
    ],
)
def test_classify_at_band_boundaries_uses_the_rounded_basis_points(
    monthly_commitment_in_rupees: str, expected_basis_points: int, expected_band: ComfortBand
) -> None:
    """Exactly 35.00% and 50.00% are Stretching; 34.99% is Comfortable and 50.01% is Risky.

    ₹3,499.50 on ₹10,000 is 34.995%, shown as 35.00%, so it is Stretching: the band never
    disagrees with the percentage shown (ADR 0020 decision 4).
    """
    ratio = ComfortRatio(
        Money.from_rupees(monthly_commitment_in_rupees), INFLOW_OF_TEN_THOUSAND_RUPEES
    )
    assert ratio.in_basis_points == expected_basis_points
    assert ComfortBandClassificationStrategy().classify(ratio) is expected_band


def test_comfort_band_classification_strategy_defaults_to_the_demo_thresholds() -> None:
    """Without injected thresholds the demo heuristics apply."""
    assert ComfortBandClassificationStrategy().thresholds is DEMO_COMFORT_THRESHOLDS


def test_classify_with_injected_thresholds_uses_them() -> None:
    """Thresholds are configuration: 30% on a 20%/40% rule is Stretching, 45% is Risky."""
    strategy = ComfortBandClassificationStrategy(ComfortThresholds(2000, 4000))
    stretching_ratio = ComfortRatio(Money.from_rupees("3000"), INFLOW_OF_TEN_THOUSAND_RUPEES)
    risky_ratio = ComfortRatio(Money.from_rupees("4500"), INFLOW_OF_TEN_THOUSAND_RUPEES)
    assert strategy.classify(stretching_ratio) is ComfortBand.STRETCHING
    assert strategy.classify(risky_ratio) is ComfortBand.RISKY


def test_comfort_band_has_exactly_three_values_in_plain_words() -> None:
    """CLAUDE.md section 2, rule 5: Comfortable, Stretching and Risky, nothing else."""
    assert [band.value for band in ComfortBand] == ["COMFORTABLE", "STRETCHING", "RISKY"]
