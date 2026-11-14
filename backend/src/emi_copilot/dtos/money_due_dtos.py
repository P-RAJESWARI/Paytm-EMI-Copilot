"""Wire schemas of "Money due from brands" (M7); the batches come from the Mock settlement port."""

from datetime import date
from typing import Annotated

from pydantic import Field

from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.settlements import BrandSettlementStatus
from emi_copilot.dtos.wire_types import (
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    PositiveAmountInPaise,
)


class BrandSettlementBatchResponse(CamelCaseResponseModel):
    """One batch of no-cost EMI sales a brand is expected to pay for, with an estimated date."""

    batch_number: Annotated[int, Field(ge=1)]
    sale_count: Annotated[int, Field(ge=0)]
    amount_in_paise: PositiveAmountInPaise
    expected_date: date
    status: BrandSettlementStatus


class MoneyDueResponse(CamelCaseResponseModel):
    """What brands still owe the shop, in batch order; not filtered by any range (plan Q13)."""

    total_due_in_paise: NonNegativeAmountInPaise
    next_expected_date: date | None
    batches: list[BrandSettlementBatchResponse]

    @classmethod
    def from_report(cls, report: MoneyDueReport) -> "MoneyDueResponse":
        """Builds the wire report."""
        return cls(
            total_due_in_paise=report.total_due.to_paise(),
            next_expected_date=report.next_expected_date,
            batches=[
                BrandSettlementBatchResponse(
                    batch_number=batch.batch_number,
                    sale_count=batch.sale_count,
                    amount_in_paise=batch.amount.to_paise(),
                    expected_date=batch.expected_date,
                    status=batch.status,
                )
                for batch in report.batches
            ],
        )
