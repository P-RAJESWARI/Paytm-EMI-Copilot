"""Where the comfort bands start, in basis points of monthly inflow; one configuration value."""

from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidComfortInputError


def _require_whole_basis_points(value: object, description: str) -> None:
    """Raises unless the value is an int number of basis points; bools are refused."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidComfortInputError(f"The {description} must be a whole number of basis points.")


@dataclass(frozen=True, slots=True)
class ComfortThresholds:
    """The two band boundaries: Stretching starts at one and Risky starts above the other.

    A ratio below stretching_from is Comfortable, one from stretching_from up to and including
    risky_above is Stretching, and anything above risky_above is Risky (ADR 0020 decision 4).
    """

    stretching_from_in_basis_points: int
    risky_above_in_basis_points: int

    def __post_init__(self) -> None:
        """Refuses non-integer thresholds and thresholds that are not above zero and in order."""
        _require_whole_basis_points(self.stretching_from_in_basis_points, "stretching threshold")
        _require_whole_basis_points(self.risky_above_in_basis_points, "risky threshold")
        if self.stretching_from_in_basis_points <= 0:
            raise InvalidComfortInputError("The stretching threshold must be above zero.")
        if self.stretching_from_in_basis_points > self.risky_above_in_basis_points:
            raise InvalidComfortInputError(
                "The stretching threshold cannot be above the risky threshold."
            )


# Demo heuristics, not a credit rule [Verify with a lender or risk team before any pilot]
# (security-and-compliance.md section 6): below 35% Comfortable, 35% to 50% Stretching, above 50%
# Risky.
DEMO_COMFORT_THRESHOLDS = ComfortThresholds(
    stretching_from_in_basis_points=3500, risky_above_in_basis_points=5000
)
