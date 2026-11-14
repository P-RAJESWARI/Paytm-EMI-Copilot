"""BrandSettlementBatch: a valid batch number, count, amount, date and status, or an error."""

from dataclasses import replace
from datetime import date

import pytest

from emi_copilot.domain.errors import InvalidReportDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.settlements import BrandSettlementBatch, BrandSettlementStatus

VALID_BATCH = BrandSettlementBatch(
    1, 18, Money.from_rupees("72000"), date(2027, 1, 13), BrandSettlementStatus.CLAIM_FILED
)


def test_a_design_batch_is_valid_and_a_batch_of_no_sales_is_allowed() -> None:
    """Batch 1: 18 sales, ₹72,000, 13 Jan 2027, claim filed; zero sales is not an error."""
    assert VALID_BATCH.amount.to_paise() == 7_200_000
    assert replace(VALID_BATCH, sale_count=0).sale_count == 0


@pytest.mark.parametrize(
    ("field_name", "bad_value", "expected_message"),
    [
        ("batch_number", 0, "batch number must be at least 1"),
        ("batch_number", True, "batch number must be a whole number"),
        ("sale_count", -1, "sale count must be at least 0"),
        ("sale_count", 2.0, "sale count must be a whole number"),
        ("amount", Money.from_paise(0), "batch amount"),
        ("amount", Money.from_rupees("0.001"), "batch amount"),
        ("expected_date", "2027-01-13", "expected date"),
        ("status", "CLAIM_FILED", "status"),
    ],
)
def test_an_inconsistent_batch_is_refused(
    field_name: str, bad_value: object, expected_message: str
) -> None:
    """Every field is checked when the batch is built."""
    with pytest.raises(InvalidReportDataError, match=expected_message):
        replace(VALID_BATCH, **{field_name: bad_value})  # type: ignore[arg-type]
