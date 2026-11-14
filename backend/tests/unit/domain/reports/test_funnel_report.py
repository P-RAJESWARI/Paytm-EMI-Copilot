"""FunnelReport: cohort counts per stage, the biggest drop, and small counts suppressed."""

from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.reports.funnel_report import (
    FUNNEL_STAGE_ORDER,
    FunnelDropSize,
    FunnelReport,
    find_biggest_drop,
)
from emi_copilot.domain.reports.small_count_suppression import (
    ReportedCount,
    SmallCountSuppressionPolicy,
)

DESIGN_WEEK_COUNTS = {
    FunnelStage.STARTED: 120,
    FunnelStage.BUDGET_TOLD: 96,
    FunnelStage.PLANS_VIEWED: 88,
    FunnelStage.AGREED: 51,
    FunnelStage.PAID: 44,
}


def test_design_week_gives_the_five_counts_and_37_lost_after_seeing_the_plans() -> None:
    """DESIGN_SPEC section 4: 120, 96, 88, 51, 44; biggest drop 37 after PLANS_VIEWED."""
    report = FunnelReport.from_stage_counts(DESIGN_WEEK_COUNTS, SmallCountSuppressionPolicy())
    assert [stage_count.stage for stage_count in report.stages] == list(FUNNEL_STAGE_ORDER)
    assert [stage_count.count.customer_count for stage_count in report.stages] == [
        120,
        96,
        88,
        51,
        44,
    ]
    assert report.biggest_drop is not None
    assert report.biggest_drop.after_stage is FunnelStage.PLANS_VIEWED
    assert report.biggest_drop.count == ReportedCount(37, is_suppressed=False)
    assert report.count_for(FunnelStage.PAID).customer_count == 44


def test_biggest_drop_tie_goes_to_the_earliest_stage() -> None:
    """10 lost after STARTED and 10 after PLANS_VIEWED: the earlier one is reported."""
    counts = {
        FunnelStage.STARTED: 40,
        FunnelStage.BUDGET_TOLD: 30,
        FunnelStage.PLANS_VIEWED: 30,
        FunnelStage.AGREED: 20,
        FunnelStage.PAID: 20,
    }
    assert find_biggest_drop(counts) == FunnelDropSize(FunnelStage.STARTED, 10)


def test_all_zero_funnel_has_no_biggest_drop_and_shows_zeros() -> None:
    """An empty shop: every stage 0 (shown, not suppressed) and no drop."""
    report = FunnelReport.from_stage_counts({}, SmallCountSuppressionPolicy())
    assert {stage_count.count for stage_count in report.stages} == {
        ReportedCount(0, is_suppressed=False)
    }
    assert report.biggest_drop is None


def test_a_funnel_that_only_rises_or_stays_has_no_drop() -> None:
    """An agreement recorded without the customer steps (Layer 2 simulator) is no drop."""
    assert find_biggest_drop({FunnelStage.STARTED: 6, FunnelStage.AGREED: 6}) == FunnelDropSize(
        FunnelStage.STARTED, 6
    )
    assert find_biggest_drop(dict.fromkeys(FUNNEL_STAGE_ORDER, 7)) is None
    assert find_biggest_drop({FunnelStage.PAID: 3}) is None


def test_small_counts_and_a_small_biggest_drop_are_suppressed() -> None:
    """7 started, 4 paid: 4 is hidden, and so is the drop of 3."""
    report = FunnelReport.from_stage_counts(
        {
            FunnelStage.STARTED: 7,
            FunnelStage.BUDGET_TOLD: 7,
            FunnelStage.PLANS_VIEWED: 7,
            FunnelStage.AGREED: 7,
            FunnelStage.PAID: 4,
        },
        SmallCountSuppressionPolicy(),
    )
    assert report.count_for(FunnelStage.STARTED) == ReportedCount(7, is_suppressed=False)
    assert report.count_for(FunnelStage.PAID) == ReportedCount(None, is_suppressed=True)
    assert report.biggest_drop is not None
    assert report.biggest_drop.after_stage is FunnelStage.AGREED
    assert report.biggest_drop.count == ReportedCount(None, is_suppressed=True)


def test_zero_stages_after_a_suppressed_stage_are_suppressed_in_a_cascade() -> None:
    """Three started and none went on: no 0 stands beside "fewer than 5" anywhere after it."""
    report = FunnelReport.from_stage_counts({FunnelStage.STARTED: 3}, SmallCountSuppressionPolicy())
    assert [stage_count.count for stage_count in report.stages] == [
        ReportedCount(None, is_suppressed=True)
    ] * len(FUNNEL_STAGE_ORDER)


def test_a_zero_after_a_shown_stage_is_still_shown() -> None:
    """Seven started and none told a budget: the 0 identifies nobody, so it stays."""
    report = FunnelReport.from_stage_counts({FunnelStage.STARTED: 7}, SmallCountSuppressionPolicy())
    assert [stage_count.count.customer_count for stage_count in report.stages] == [7, 0, 0, 0, 0]


def test_a_shown_count_after_a_suppressed_stage_keeps_its_number() -> None:
    """Only zeros follow suppression; a rise to 5 or more is shown (agreements without steps)."""
    report = FunnelReport.from_stage_counts(
        {FunnelStage.STARTED: 9, FunnelStage.BUDGET_TOLD: 2, FunnelStage.AGREED: 6},
        SmallCountSuppressionPolicy(),
    )
    assert [stage_count.count.customer_count for stage_count in report.stages] == [
        9,
        None,
        None,
        6,
        0,
    ]


def test_a_drop_beside_a_suppressed_stage_is_suppressed_so_it_cannot_be_subtracted() -> None:
    """20 started and 3 told a budget: showing a drop of 17 would reveal the hidden 3."""
    report = FunnelReport.from_stage_counts(
        {FunnelStage.STARTED: 20, FunnelStage.BUDGET_TOLD: 3}, SmallCountSuppressionPolicy()
    )
    assert report.count_for(FunnelStage.BUDGET_TOLD) == ReportedCount(None, is_suppressed=True)
    assert report.biggest_drop is not None
    assert report.biggest_drop.after_stage is FunnelStage.STARTED
    assert report.biggest_drop.count == ReportedCount(None, is_suppressed=True)


def test_a_drop_whose_earlier_stage_is_suppressed_is_suppressed() -> None:
    """A later stage of 0 after a hidden 4 is itself hidden, and so is the drop between them."""
    report = FunnelReport.from_stage_counts(
        {FunnelStage.STARTED: 9, FunnelStage.BUDGET_TOLD: 9, FunnelStage.PLANS_VIEWED: 4},
        SmallCountSuppressionPolicy(),
    )
    assert report.biggest_drop is not None
    assert report.biggest_drop.after_stage is FunnelStage.BUDGET_TOLD
    assert report.biggest_drop.count == ReportedCount(None, is_suppressed=True)
