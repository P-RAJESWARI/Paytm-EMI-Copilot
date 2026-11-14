"""SmallCountSuppressionPolicy: hides report counts from 1 to 4 (owner decision, plan Q3)."""

from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidReportDataError

MINIMUM_SHOWN_CUSTOMER_COUNT = 5
"""A count of 1 to 4 customers could point at one person, so it is shown as "fewer than 5"."""


# Pattern: Value Object. A count as the merchant may see it: shown, or suppressed with no number.
@dataclass(frozen=True, slots=True)
class ReportedCount:
    """A customer count; when suppressed, customer_count is None and only the flag is sent."""

    customer_count: int | None
    is_suppressed: bool

    def __post_init__(self) -> None:
        """Rejects a suppressed count that still carries a number, or a shown one without one."""
        if self.is_suppressed != (self.customer_count is None):
            raise InvalidReportDataError("A suppressed count has no number; a shown one has one.")


class SmallCountSuppressionPolicy:
    """The one rule every report applies to a count: zero and 5 or more are shown, 1 to 4 are not.

    Zero is shown because it identifies nobody, and the empty report must read as empty; the one
    exception is a zero that follows a suppressed count in a sequence (report_after).
    """

    def __init__(self, minimum_shown_count: int = MINIMUM_SHOWN_CUSTOMER_COUNT) -> None:
        """Keeps the smallest non-zero count that may be shown (5 by owner decision)."""
        self._minimum_shown_count = minimum_shown_count

    @property
    def minimum_shown_count(self) -> int:
        """Gives the smallest non-zero count that is shown with its number."""
        return self._minimum_shown_count

    def report(self, customer_count: int) -> ReportedCount:
        """Gives the count as shown: zero and counts at the threshold or above keep their number."""
        if isinstance(customer_count, bool) or not isinstance(customer_count, int):
            raise InvalidReportDataError("A customer count must be a whole number.")
        if customer_count < 0:
            raise InvalidReportDataError("A customer count cannot be negative.")
        if 0 < customer_count < self._minimum_shown_count:
            return ReportedCount(customer_count=None, is_suppressed=True)
        return ReportedCount(customer_count=customer_count, is_suppressed=False)

    def report_after(self, customer_count: int, previous_count: ReportedCount) -> ReportedCount:
        """Reports a count that follows another in a sequence, such as the next funnel stage.

        A zero right after a suppressed count is suppressed too: a 0 beside "fewer than 5" would
        tell the merchant that those few customers all stopped at the earlier step.
        """
        reported_count = self.report(customer_count)
        if previous_count.is_suppressed and customer_count == 0:
            return ReportedCount(customer_count=None, is_suppressed=True)
        return reported_count
