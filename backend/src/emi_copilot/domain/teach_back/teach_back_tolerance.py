"""TeachBackTolerance: how far the customer's monthly figure may be from the plan's."""

from dataclasses import dataclass
from decimal import Decimal

from emi_copilot.domain.ai_errors import InvalidTeachBackInputError


# Pattern: Value Object. One place holds the heuristic, so it can be tuned with a lender.
@dataclass(frozen=True, slots=True)
class TeachBackTolerance:
    """The allowed gap as a share of the plan's monthly amount, between 0 and 1 (exclusive)."""

    monthly_amount_share: Decimal

    def __post_init__(self) -> None:
        """Rejects a share that is not a Decimal from 0 up to (not including) 1."""
        share = self.monthly_amount_share
        if not isinstance(share, Decimal) or not Decimal(0) <= share < Decimal(1):
            raise InvalidTeachBackInputError("A teach-back tolerance must be a Decimal in [0, 1).")


DEMO_TEACH_BACK_TOLERANCE = TeachBackTolerance(monthly_amount_share=Decimal("0.05"))
"""Demo heuristic, plan Q7: within 5% of the monthly amount ("about ₹3,700" for ₹3,667). [Verify]
with the lender or a consumer-research partner before any pilot."""
