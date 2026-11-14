"""Budget buckets: inclusive lower bounds, hidden under 5 tellers, plans placed by monthly."""

import pytest

from emi_copilot.domain.errors import InvalidReportDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.reports.budget_buckets import (
    BUDGET_RANGES,
    BucketPlan,
    BudgetRange,
    build_budget_bucket_report,
    build_budget_ranges,
)
from emi_copilot.domain.reports.small_count_suppression import (
    ReportedCount,
    SmallCountSuppressionPolicy,
)
from tests.report_builders import build_phone_128_gb_offers

DESIGN_BUCKET_COUNTS = (5, 7, 14, 21, 49)
THREE_THOUSAND_RUPEES = Money.from_rupees("3000")


def _find_range_index(monthly_in_rupees: str) -> int:
    """Gives the index of the one range that holds the amount."""
    amount = Money.from_rupees(monthly_in_rupees)
    (index,) = [
        index for index, budget_range in enumerate(BUDGET_RANGES) if budget_range.contains(amount)
    ]
    return index


def test_budget_ranges_are_the_five_m5_buckets() -> None:
    """Under ₹2,500 up to ₹4,000 and above, the last one open."""
    assert [
        (budget_range.lower_bound.to_paise(), budget_range.upper_bound)
        for budget_range in BUDGET_RANGES
    ] == [
        (0, Money.from_rupees("2500")),
        (250_000, Money.from_rupees("3000")),
        (300_000, Money.from_rupees("3500")),
        (350_000, Money.from_rupees("4000")),
        (400_000, None),
    ]


@pytest.mark.parametrize(
    ("monthly_in_rupees", "expected_index"),
    [
        ("2499.99", 0),
        ("2500", 1),
        ("2999.99", 1),
        ("3000", 2),
        ("3666.67", 3),
        ("4000", 4),
        ("100000", 4),
    ],
)
def test_each_bucket_includes_its_lower_bound_and_excludes_its_upper_bound(
    monthly_in_rupees: str, expected_index: int
) -> None:
    """Exactly ₹2,500 is in the second bucket and exactly ₹3,000 in the third."""
    assert _find_range_index(monthly_in_rupees) == expected_index


def test_build_budget_ranges_refuses_boundaries_that_do_not_increase() -> None:
    """Overlapping buckets would count a customer twice."""
    with pytest.raises(InvalidReportDataError, match="increasing"):
        build_budget_ranges((Money.from_rupees("3000"), Money.from_rupees("3000")))


def test_design_buckets_show_counts_ceiling_flags_and_the_insight_plans() -> None:
    """5, 7, 14, 21, 49 (96 in total); the two under ₹3,000 are under the ceiling."""
    report = build_budget_bucket_report(
        DESIGN_BUCKET_COUNTS,
        THREE_THOUSAND_RUPEES,
        build_phone_128_gb_offers(),
        SmallCountSuppressionPolicy(),
    )
    assert report.total_count == ReportedCount(96, is_suppressed=False)
    assert report.are_buckets_hidden is False
    assert [bucket.count.customer_count for bucket in report.buckets] == list(DESIGN_BUCKET_COUNTS)
    assert [bucket.is_under_ceiling for bucket in report.buckets] == [
        True,
        True,
        False,
        False,
        False,
    ]
    assert [bucket.plans for bucket in report.buckets] == [
        (BucketPlan(EmiType.STANDARD, "Cardless lender", Money.from_rupees("2050")),),
        (),
        (),
        (
            BucketPlan(EmiType.NO_COST, "Brand", Money.from_rupees("3666.67")),
            BucketPlan(EmiType.STANDARD, "Your card's bank", Money.from_rupees("3850")),
        ),
        (),
    ]


def test_buckets_are_hidden_when_four_customers_told_a_budget() -> None:
    """Fewer than 5 budget tellers: no bucket at all, and the total is suppressed too."""
    report = build_budget_bucket_report((1, 1, 1, 1, 0), None, (), SmallCountSuppressionPolicy())
    assert report.are_buckets_hidden is True
    assert report.buckets == ()
    assert report.total_count == ReportedCount(None, is_suppressed=True)


def test_buckets_are_shown_at_five_tellers_with_each_small_count_suppressed() -> None:
    """Five tellers: the buckets appear, each count of 1 to 4 still hidden; zero is shown."""
    report = build_budget_bucket_report((1, 4, 0, 0, 0), None, (), SmallCountSuppressionPolicy())
    assert report.are_buckets_hidden is False
    assert report.total_count == ReportedCount(5, is_suppressed=False)
    assert [bucket.count for bucket in report.buckets][:3] == [
        ReportedCount(None, is_suppressed=True),
        ReportedCount(None, is_suppressed=True),
        ReportedCount(0, is_suppressed=False),
    ]
    assert not any(bucket.is_under_ceiling for bucket in report.buckets)
    assert all(bucket.plans == () for bucket in report.buckets)


def test_no_budget_tellers_hides_the_buckets_and_shows_a_zero_total() -> None:
    """The empty shop's shape."""
    report = build_budget_bucket_report((0, 0, 0, 0, 0), None, (), SmallCountSuppressionPolicy())
    assert report.are_buckets_hidden is True
    assert report.total_count == ReportedCount(0, is_suppressed=False)


def test_build_budget_bucket_report_refuses_a_count_list_of_the_wrong_length() -> None:
    """One count per range, no more and no fewer."""
    with pytest.raises(InvalidReportDataError, match="one customer count per"):
        build_budget_bucket_report((5, 7), None, (), SmallCountSuppressionPolicy())


def test_budget_range_without_upper_bound_is_open() -> None:
    """₹4,000 and above has no end."""
    assert BudgetRange(Money.from_rupees("4000"), None).contains(Money.from_rupees("9999999"))
