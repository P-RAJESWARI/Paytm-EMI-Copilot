"""MoneyDueReport: what brands still owe the shop in total, when the next payment is expected."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from emi_copilot.domain.errors import InvalidReportDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.settlements import BrandSettlementBatch


@dataclass(frozen=True, slots=True)
class MoneyDueReport:
    """Every expected batch in batch order, their total and the earliest expected date.

    It is not filtered by the report range (plan Q13): money due is what is still to come.
    """

    total_due: Money
    next_expected_date: date | None
    batches: tuple[BrandSettlementBatch, ...]

    @classmethod
    def from_batches(cls, batches: Sequence[BrandSettlementBatch]) -> "MoneyDueReport":
        """Totals the batches; two batches with one number are refused, never merged."""
        batch_numbers = [batch.batch_number for batch in batches]
        if len(set(batch_numbers)) != len(batch_numbers):
            raise InvalidReportDataError("Each settlement batch must have its own number.")
        return cls(
            total_due=sum((batch.amount for batch in batches), Money.from_paise(0)),
            next_expected_date=min((batch.expected_date for batch in batches), default=None),
            batches=tuple(sorted(batches, key=lambda batch: batch.batch_number)),
        )
