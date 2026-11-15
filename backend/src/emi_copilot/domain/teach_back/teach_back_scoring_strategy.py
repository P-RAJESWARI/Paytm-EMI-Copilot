"""TeachBackScoringStrategy: scores the numbers a customer said against the plan's terms."""

from decimal import Decimal

from emi_copilot.domain.teach_back.teach_back_result import TeachBackResult
from emi_copilot.domain.teach_back.teach_back_tolerance import (
    DEMO_TEACH_BACK_TOLERANCE,
    TeachBackTolerance,
)


# Pattern: Strategy. The scoring rule can change (a tighter tolerance, the extra as well)
# without touching the flow that extracts numbers or words the feedback.
class TeachBackScoringStrategy:
    """CLOSE_ENOUGH when one number is the tenure exactly and another is near the monthly amount.

    Deterministic and LLM-free: the customer's words never reach an AI model (plan Q7).
    """

    def __init__(self, tolerance: TeachBackTolerance = DEMO_TEACH_BACK_TOLERANCE) -> None:
        """Keeps the tolerance for the monthly amount."""
        self._tolerance = tolerance

    def score(
        self, stated_numbers: tuple[int, ...], monthly_in_rupees: int, tenure_in_months: int
    ) -> TeachBackResult:
        """Needs the tenure said exactly and a different number within the monthly tolerance."""
        for tenure_position, stated_number in enumerate(stated_numbers):
            if stated_number != tenure_in_months:
                continue
            if any(
                self.is_near_monthly_amount(other_number, monthly_in_rupees)
                for other_position, other_number in enumerate(stated_numbers)
                if other_position != tenure_position
            ):
                return TeachBackResult.CLOSE_ENOUGH
        return TeachBackResult.TRY_AGAIN

    def is_near_monthly_amount(self, stated_amount: int, monthly_in_rupees: int) -> bool:
        """Tells whether a stated amount is within the tolerance; exactly at the edge counts."""
        allowed_gap = Decimal(monthly_in_rupees) * self._tolerance.monthly_amount_share
        return abs(Decimal(stated_amount) - Decimal(monthly_in_rupees)) <= allowed_gap
