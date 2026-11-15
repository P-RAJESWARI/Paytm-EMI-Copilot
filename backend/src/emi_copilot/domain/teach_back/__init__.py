"""Teach-back (C8): an optional, advisory check that the customer understood the plan's terms."""

from emi_copilot.domain.teach_back.teach_back_result import TeachBackResult
from emi_copilot.domain.teach_back.teach_back_scoring_strategy import TeachBackScoringStrategy
from emi_copilot.domain.teach_back.teach_back_tolerance import (
    DEMO_TEACH_BACK_TOLERANCE,
    TeachBackTolerance,
)

__all__ = [
    "DEMO_TEACH_BACK_TOLERANCE",
    "TeachBackResult",
    "TeachBackScoringStrategy",
    "TeachBackTolerance",
]
