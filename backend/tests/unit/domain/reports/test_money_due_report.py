"""MoneyDueReport: the batches in order, their total and the earliest expected date."""

from datetime import date

import pytest

from emi_copilot.domain.errors import InvalidReportDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from tests.report_builders import build_design_settlement_batches


def test_design_batches_total_1_84_000_with_the_first_payment_on_13_january() -> None:
    """DESIGN_SPEC section 4 money due."""
    report = MoneyDueReport.from_batches(build_design_settlement_batches())
    assert report.total_due == Money.from_rupees("184000")
    assert report.next_expected_date == date(2027, 1, 13)
    assert [batch.batch_number for batch in report.batches] == [1, 2, 3]


def test_no_batches_give_nothing_due_and_no_date() -> None:
    """Another shop's empty shape."""
    report = MoneyDueReport.from_batches(())
    assert (report.total_due, report.next_expected_date, report.batches) == (
        Money.from_paise(0),
        None,
        (),
    )


def test_two_batches_with_one_number_are_refused() -> None:
    """Batches are never merged or silently dropped."""
    first_batch = build_design_settlement_batches()[1]
    with pytest.raises(InvalidReportDataError, match="own number"):
        MoneyDueReport.from_batches((first_batch, first_batch))
