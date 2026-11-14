"""Puts a comfort ratio into one of the three comfort bands."""

from emi_copilot.domain.comfort.comfort_band import ComfortBand
from emi_copilot.domain.comfort.comfort_ratio import ComfortRatio
from emi_copilot.domain.comfort.comfort_thresholds import (
    DEMO_COMFORT_THRESHOLDS,
    ComfortThresholds,
)


# Pattern: Strategy. The band rule is swappable through injected thresholds; one concrete class,
# so no abstract base until a second rule is needed (design-patterns.md section 3).
class ComfortBandClassificationStrategy:
    """Classifies on the rounded basis points shown, so the percentage and band always agree."""

    def __init__(self, thresholds: ComfortThresholds = DEMO_COMFORT_THRESHOLDS) -> None:
        """Stores the band thresholds; the demo heuristics are the default (ADR 0020)."""
        self._thresholds = thresholds

    @property
    def thresholds(self) -> ComfortThresholds:
        """Gives the thresholds this strategy classifies with."""
        return self._thresholds

    def classify(self, ratio: ComfortRatio) -> ComfortBand:
        """Gives Comfortable below stretching_from, Risky above risky_above, else Stretching."""
        ratio_in_basis_points = ratio.in_basis_points
        if ratio_in_basis_points < self._thresholds.stretching_from_in_basis_points:
            return ComfortBand.COMFORTABLE
        if ratio_in_basis_points > self._thresholds.risky_above_in_basis_points:
            return ComfortBand.RISKY
        return ComfortBand.STRETCHING
