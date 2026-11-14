"""ComfortRatio: the share of monthly inflow that monthly EMI payments take, kept exact."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, DivisionByZero, Inexact, InvalidOperation, Overflow

from emi_copilot.domain.errors import InvalidComfortInputError
from emi_copilot.domain.money import Money

# A private context, so the thread's global Decimal context is never read or mutated. divmod gives
# the exact whole quotient and remainder, so half-up rounding to a basis point is exact. Money has
# at most 34 digits, so 80 digits keep every step exact, and Inexact traps if one ever is not.
_RATIO_ARITHMETIC_CONTEXT = Context(
    prec=80,
    rounding=ROUND_HALF_UP,
    traps=[DivisionByZero, Inexact, InvalidOperation, Overflow],
)
_BASIS_POINTS_PER_WHOLE_POWER_OF_TEN = 4


def _require_money(value: object, description: str) -> None:
    """Raises unless the value is Money."""
    if not isinstance(value, Money):
        raise InvalidComfortInputError(f"The {description} must be Money.")


# Pattern: Value Object. Holds the exact ratio and owns its one rounding to basis points.
@dataclass(frozen=True, slots=True)
class ComfortRatio:
    """Monthly commitment divided by monthly inflow, held as the two exact amounts.

    Nothing is rounded until `in_basis_points`, which rounds half-up once. Ratios above 100% are
    allowed: they are the honest answer when payments exceed the inflow.
    """

    monthly_commitment: Money
    monthly_inflow: Money

    def __post_init__(self) -> None:
        """Refuses amounts that are not Money and an inflow of zero, which has no ratio."""
        _require_money(self.monthly_commitment, "monthly commitment")
        _require_money(self.monthly_inflow, "monthly inflow")
        if self.monthly_inflow.is_zero:
            raise InvalidComfortInputError("The monthly inflow must be above zero rupees.")

    @property
    def in_basis_points(self) -> int:
        """Gives the ratio in basis points (3890 means 38.90%), rounded half-up exactly once."""
        commitment_times_basis_points = self.monthly_commitment.amount_in_rupees.scaleb(
            _BASIS_POINTS_PER_WHOLE_POWER_OF_TEN, _RATIO_ARITHMETIC_CONTEXT
        )
        whole_basis_points, remainder = _RATIO_ARITHMETIC_CONTEXT.divmod(
            commitment_times_basis_points, self.monthly_inflow.amount_in_rupees
        )
        twice_the_remainder = _RATIO_ARITHMETIC_CONTEXT.multiply(remainder, 2)
        is_half_or_more = twice_the_remainder >= self.monthly_inflow.amount_in_rupees
        return int(whole_basis_points) + (1 if is_half_or_more else 0)
