"""SmallCountSuppressionPolicy: 0 and 5 or more are shown; 1 to 4 become "fewer than 5"."""

import pytest

from emi_copilot.domain.errors import InvalidReportDataError
from emi_copilot.domain.reports.small_count_suppression import (
    MINIMUM_SHOWN_CUSTOMER_COUNT,
    ReportedCount,
    SmallCountSuppressionPolicy,
)


@pytest.mark.parametrize(
    ("customer_count", "expected_reported_count"),
    [
        (0, ReportedCount(0, is_suppressed=False)),
        (1, ReportedCount(None, is_suppressed=True)),
        (4, ReportedCount(None, is_suppressed=True)),
        (5, ReportedCount(5, is_suppressed=False)),
        (120, ReportedCount(120, is_suppressed=False)),
    ],
)
def test_report_shows_zero_and_five_or_more_and_suppresses_one_to_four(
    customer_count: int, expected_reported_count: ReportedCount
) -> None:
    """Owner decision Q3: a suppressed count carries no number at all."""
    assert SmallCountSuppressionPolicy().report(customer_count) == expected_reported_count


def test_default_threshold_is_five() -> None:
    """One threshold for every report."""
    assert SmallCountSuppressionPolicy().minimum_shown_count == MINIMUM_SHOWN_CUSTOMER_COUNT == 5


@pytest.mark.parametrize("not_a_count", [-1, True, 2.0])
def test_report_refuses_a_negative_or_non_integer_count(not_a_count: object) -> None:
    """A count is a whole number of customers."""
    with pytest.raises(InvalidReportDataError, match="count"):
        SmallCountSuppressionPolicy().report(not_a_count)  # type: ignore[arg-type]


@pytest.mark.parametrize(("customer_count", "is_suppressed"), [(3, True), (None, False)])
def test_reported_count_refuses_a_number_that_contradicts_its_flag(
    customer_count: int | None, is_suppressed: bool
) -> None:
    """A suppressed count cannot leak its number, and a shown one must have one."""
    with pytest.raises(InvalidReportDataError, match="suppressed"):
        ReportedCount(customer_count, is_suppressed=is_suppressed)


@pytest.mark.parametrize(
    ("customer_count", "previous_count", "expected_reported_count"),
    [
        (0, ReportedCount(None, is_suppressed=True), ReportedCount(None, is_suppressed=True)),
        (0, ReportedCount(7, is_suppressed=False), ReportedCount(0, is_suppressed=False)),
        (0, ReportedCount(0, is_suppressed=False), ReportedCount(0, is_suppressed=False)),
        (3, ReportedCount(9, is_suppressed=False), ReportedCount(None, is_suppressed=True)),
        (6, ReportedCount(None, is_suppressed=True), ReportedCount(6, is_suppressed=False)),
    ],
)
def test_report_after_suppresses_a_zero_that_follows_a_suppressed_count(
    customer_count: int, previous_count: ReportedCount, expected_reported_count: ReportedCount
) -> None:
    """A 0 beside "fewer than 5" would show where those few stopped; other counts as usual."""
    policy = SmallCountSuppressionPolicy()
    assert policy.report_after(customer_count, previous_count) == expected_reported_count


def test_report_after_still_refuses_a_non_integer_count() -> None:
    """The sequence rule never skips the count's own checks."""
    with pytest.raises(InvalidReportDataError, match="count"):
        SmallCountSuppressionPolicy().report_after(
            False,
            ReportedCount(None, is_suppressed=True),
        )
