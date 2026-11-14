"""Comfort check: ratio of monthly EMIs to inflow and its band; advice, not a credit decision."""

from emi_copilot.domain.comfort.comfort_assessment import ComfortAssessment, assess_comfort
from emi_copilot.domain.comfort.comfort_band import ComfortBand
from emi_copilot.domain.comfort.comfort_band_classification_strategy import (
    ComfortBandClassificationStrategy,
)
from emi_copilot.domain.comfort.comfort_ratio import ComfortRatio
from emi_copilot.domain.comfort.comfort_thresholds import (
    DEMO_COMFORT_THRESHOLDS,
    ComfortThresholds,
)
from emi_copilot.domain.comfort.financial_profile import FinancialProfile

__all__ = [
    "DEMO_COMFORT_THRESHOLDS",
    "ComfortAssessment",
    "ComfortBand",
    "ComfortBandClassificationStrategy",
    "ComfortRatio",
    "ComfortThresholds",
    "FinancialProfile",
    "assess_comfort",
]
