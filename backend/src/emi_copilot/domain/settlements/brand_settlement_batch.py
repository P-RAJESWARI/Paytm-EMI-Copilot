"""BrandSettlementBatch: one batch of no-cost EMI sales a brand is expected to pay the shop for."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from emi_copilot.domain.errors import InvalidReportDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import require_positive_whole_paise_money


class BrandSettlementStatus(StrEnum):
    """Where a batch's payment from the brand stands (M7's status chips)."""

    CLAIM_FILED = "CLAIM_FILED"
    """The claim for the batch has been filed with the brand."""

    WAITING_FOR_BRAND = "WAITING_FOR_BRAND"
    """The claim is with the brand, which has not paid yet."""

    NOT_YET_DUE = "NOT_YET_DUE"
    """The batch cannot be claimed yet under the brand's offer terms."""


# Pattern: Value Object. A settlement batch as the settlement port reports it.
@dataclass(frozen=True, slots=True)
class BrandSettlementBatch:
    """A numbered batch: how many sales, how much is due, and the estimated payment date."""

    batch_number: int
    sale_count: int
    amount: Money
    expected_date: date
    status: BrandSettlementStatus

    def __post_init__(self) -> None:
        """Rejects a batch number below one, a negative count, a zero amount or a bad status."""
        for whole_number, description, minimum in (
            (self.batch_number, "batch number", 1),
            (self.sale_count, "sale count", 0),
        ):
            if isinstance(whole_number, bool) or not isinstance(whole_number, int):
                raise InvalidReportDataError(f"The {description} must be a whole number.")
            if whole_number < minimum:
                raise InvalidReportDataError(f"The {description} must be at least {minimum}.")
        require_positive_whole_paise_money(self.amount, "batch amount", InvalidReportDataError)
        if not isinstance(self.expected_date, date):
            raise InvalidReportDataError("The expected date must be a date.")
        if not isinstance(self.status, BrandSettlementStatus):
            raise InvalidReportDataError("The status must be a BrandSettlementStatus.")
