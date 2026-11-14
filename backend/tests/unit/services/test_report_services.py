"""Report services on fakes: shop-scoped counts, missed sales, actions, money due, messages."""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from emi_copilot.domain.errors import InvalidReportingPeriodError
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.funnel_report import FunnelReport
from emi_copilot.domain.reports.missed_sales import MissedSalesReport
from emi_copilot.domain.reports.reporting_period import ReportingRange
from emi_copilot.domain.reports.small_count_suppression import ReportedCount
from emi_copilot.domain.reports.suggested_actions import (
    CheaperModelAction,
    LongerNoCostPlanAction,
    SuggestedAction,
)
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessages
from emi_copilot.domain.sales import SaleStatus
from tests.payment_builders import CREATED_AT
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.report_service_wiring import (
    PHONE_64_GB_ID,
    PHONE_128_GB_ID,
    ReportServices,
    SyntheticWeek,
    build_report_services,
    store_synthetic_week,
)
from tests.unit.services.sale_service_wiring import OTHER_PRINCIPAL, PRINCIPAL

CURRENT_WEEK_MONDAY = date(2026, 11, 9)


def test_funnel_report_counts_this_weeks_cohort_of_the_shop_only(kit: ServiceTestKit) -> None:
    """Nine of the shop's sales this week; another shop's and last week's are not counted."""
    store_synthetic_week(kit)
    view = build_report_services(kit).funnel.get_funnel_report(PRINCIPAL, ReportingRange.THIS_WEEK)
    assert view.reporting_range is ReportingRange.THIS_WEEK
    assert (view.period.period_start_date, view.period.period_end_date) == (
        CURRENT_WEEK_MONDAY,
        date(2026, 11, 15),
    )
    assert [stage.count.customer_count for stage in view.report.stages] == [9, 9, 9, None, None]
    assert view.report.count_for(FunnelStage.AGREED) == ReportedCount(None, is_suppressed=True)
    # PAID is 0 right after the suppressed AGREED, so it is suppressed too.
    assert view.report.count_for(FunnelStage.PAID) == ReportedCount(None, is_suppressed=True)
    assert view.report.biggest_drop is not None
    assert view.report.biggest_drop.after_stage is FunnelStage.PLANS_VIEWED


def test_another_shop_sees_only_its_own_single_sale_suppressed(kit: ServiceTestKit) -> None:
    """Cross-merchant isolation: one sale is "fewer than 5", never the first shop's nine."""
    store_synthetic_week(kit)
    view = build_report_services(kit).funnel.get_funnel_report(
        OTHER_PRINCIPAL, ReportingRange.THIS_WEEK
    )
    assert view.report.count_for(FunnelStage.STARTED) == ReportedCount(None, is_suppressed=True)


def test_missed_sales_report_finds_six_missed_on_the_128_gb_phone_under_3000(
    kit: ServiceTestKit,
) -> None:
    """The 64 GB budget of ₹3,100 fits its ₹3,000 plan; agreed sales are not missed."""
    store_synthetic_week(kit)
    view = build_report_services(kit).missed_sales.get_missed_sales_report(
        PRINCIPAL, ReportingRange.THIS_WEEK
    )
    report = view.report
    assert report.missed_count == ReportedCount(6, is_suppressed=False)
    assert report.budget_ceiling == Money.from_rupees("3000")
    assert report.product_insight is not None
    assert report.product_insight.product_id == PHONE_128_GB_ID
    assert report.product_insight.lowest_no_extra_cost_monthly == Money.from_rupees("3666.67")
    cheapest = report.product_insight.cheapest_plan_under_ceiling
    assert cheapest is not None
    assert cheapest.quoted_monthly_installment == Money.from_rupees("2050")
    assert [bucket.count.customer_count for bucket in report.budget_buckets.buckets] == [
        None,
        5,
        None,
        0,
        0,
    ]
    assert report.budget_buckets.total_count.customer_count == 9


def test_missed_sales_report_of_today_without_sales_is_empty(kit: ServiceTestKit) -> None:
    """The empty shape: nothing missed, buckets hidden, no insight product."""
    view = build_report_services(kit).missed_sales.get_missed_sales_report(
        PRINCIPAL, ReportingRange.TODAY
    )
    assert view.report.missed_count == ReportedCount(0, is_suppressed=False)
    assert view.report.product_insight is None
    assert view.report.budget_buckets.are_buckets_hidden is True


def test_suggested_actions_are_the_longer_no_cost_plan_then_the_64_gb_phone(
    kit: ServiceTestKit,
) -> None:
    """Both strategies fire on the synthetic week, in strategy order."""
    store_synthetic_week(kit)
    actions = build_report_services(kit).suggested_actions.get_suggested_actions(
        PRINCIPAL, ReportingRange.THIS_MONTH
    )
    assert [type(action) for action in actions] == [LongerNoCostPlanAction, CheaperModelAction]
    assert isinstance(actions[1], CheaperModelAction)
    assert actions[1].product_id == PHONE_64_GB_ID


def test_money_due_comes_from_the_settlement_port_for_the_shops_code(kit: ServiceTestKit) -> None:
    """The demo shop gets ₹1,84,000; a shop the Mock does not know gets nothing."""
    services = build_report_services(kit)
    demo_shop = replace(PRINCIPAL, shop_code="RAVI-0193")
    assert services.money_due.get_money_due(demo_shop).total_due == Money.from_rupees("184000")
    assert services.money_due.get_money_due(PRINCIPAL).batches == ()


def test_weekly_message_defaults_to_this_week_and_is_not_sent_yet(kit: ServiceTestKit) -> None:
    """The text is written from this week's numbers; nothing is delivered by reading it."""
    store_synthetic_week(kit)
    services = build_report_services(kit)
    view = services.weekly_message.get_weekly_message(PRINCIPAL, None)
    assert view.period.period_start_date == CURRENT_WEEK_MONDAY
    assert view.sent_at is None
    assert view.messages.english.title == "Your EMI sales, 9 to 15 November"
    assert (
        "6 customers wanted under ₹3,000 a month with nothing extra, and no plan fit."
        in view.messages.english.paragraphs[1]
    )
    assert services.delivery.deliveries == []


def test_sending_the_weekly_message_twice_records_and_delivers_it_once(kit: ServiceTestKit) -> None:
    """The second send keeps the first moment and delivers nothing more."""
    store_synthetic_week(kit)
    services = build_report_services(kit)
    first = services.weekly_message.send_weekly_message(PRINCIPAL, CURRENT_WEEK_MONDAY)
    kit.clock.advance(timedelta(minutes=3))
    second = services.weekly_message.send_weekly_message(PRINCIPAL, CURRENT_WEEK_MONDAY)
    read_back = services.weekly_message.get_weekly_message(PRINCIPAL, CURRENT_WEEK_MONDAY)
    assert first.sent_at == second.sent_at == read_back.sent_at == CREATED_AT
    assert len(services.delivery.deliveries) == 1
    assert services.delivery.deliveries[0].messages == first.messages


def test_weekly_message_of_another_shop_is_not_marked_sent(kit: ServiceTestKit) -> None:
    """Sending is per shop."""
    services = build_report_services(kit)
    services.weekly_message.send_weekly_message(PRINCIPAL, CURRENT_WEEK_MONDAY)
    assert services.weekly_message.get_weekly_message(OTHER_PRINCIPAL, None).sent_at is None


@pytest.mark.parametrize(
    ("period_start_date", "expected_message"),
    [(date(2026, 11, 16), "not started"), (date(2026, 11, 10), "Monday")],
)
def test_weekly_message_refuses_a_future_week_or_a_day_that_is_not_monday(
    kit: ServiceTestKit, period_start_date: date, expected_message: str
) -> None:
    """Next week's message cannot exist yet; weeks start on Monday."""
    with pytest.raises(InvalidReportingPeriodError, match=expected_message):
        build_report_services(kit).weekly_message.send_weekly_message(PRINCIPAL, period_start_date)


def test_weekly_message_of_a_past_week_can_be_read(kit: ServiceTestKit) -> None:
    """Last week's message counts last week's single missed sale (suppressed, so not said)."""
    store_synthetic_week(kit)
    view = build_report_services(kit).weekly_message.get_weekly_message(
        PRINCIPAL, date(2026, 11, 2)
    )
    assert view.messages.english.title == "Your EMI sales, 2 to 8 November"
    assert "wanted under" not in " ".join(view.messages.english.paragraphs)


EveryReport = tuple[FunnelReport, MissedSalesReport, tuple[SuggestedAction, ...], WeeklyMessages]


def _read_every_report(services: ReportServices, reporting_range: ReportingRange) -> EveryReport:
    """Reads the funnel, missed sales, actions and this week's message as the merchant would."""
    return (
        services.funnel.get_funnel_report(PRINCIPAL, reporting_range).report,
        services.missed_sales.get_missed_sales_report(PRINCIPAL, reporting_range).report,
        services.suggested_actions.get_suggested_actions(PRINCIPAL, reporting_range),
        services.weekly_message.get_weekly_message(PRINCIPAL, None).messages,
    )


@pytest.mark.parametrize("reporting_range", list(ReportingRange))
def test_a_sale_still_choosing_never_changes_any_report(
    kit: ServiceTestKit, reporting_range: ReportingRange
) -> None:
    """Rule 6: a customer at the counter with a low budget and the plans seen adds nothing."""
    week = store_synthetic_week(kit)
    services = build_report_services(kit)
    before = _read_every_report(services, reporting_range)
    week.store_sale(
        FunnelStage.PLANS_VIEWED,
        "1000",
        started_at=kit.clock.now() - timedelta(minutes=5),
        status=SaleStatus.CHOOSING,
    )
    assert _read_every_report(services, reporting_range) == before


def test_today_with_one_customer_choosing_after_a_low_budget_shows_nothing_of_them(
    kit: ServiceTestKit,
) -> None:
    """The only sale today is still choosing: zeros, no ceiling, no product, no action."""
    SyntheticWeek(kit).store_sale(FunnelStage.PLANS_VIEWED, "2400", status=SaleStatus.CHOOSING)
    funnel, missed_sales, actions, messages = _read_every_report(
        build_report_services(kit), ReportingRange.TODAY
    )
    assert [stage.count for stage in funnel.stages] == [ReportedCount(0, is_suppressed=False)] * 5
    assert missed_sales.missed_count == ReportedCount(0, is_suppressed=False)
    assert (missed_sales.budget_ceiling, missed_sales.product_insight) == (None, None)
    assert actions == ()
    assert messages.english.paragraphs == ("No EMI sales this week yet.",)


def test_a_suppressed_missed_count_hides_every_figure_derived_from_it(kit: ServiceTestKit) -> None:
    """Three missed of eight budgets: no ceiling, product, under-ceiling bucket or action."""
    week = SyntheticWeek(kit)
    for budget_in_rupees in ("2400", "2600", "2900"):
        week.store_sale(FunnelStage.PLANS_VIEWED, budget_in_rupees)
    for _ in range(5):
        week.store_sale(FunnelStage.AGREED, "3200")
    services = build_report_services(kit)
    report = services.missed_sales.get_missed_sales_report(
        PRINCIPAL, ReportingRange.THIS_WEEK
    ).report
    actions = services.suggested_actions.get_suggested_actions(PRINCIPAL, ReportingRange.THIS_WEEK)
    message = services.weekly_message.get_weekly_message(PRINCIPAL, None).messages.english
    assert report.missed_count == ReportedCount(None, is_suppressed=True)
    assert (report.budget_ceiling, report.product_insight) == (None, None)
    assert report.budget_buckets.are_buckets_hidden is False
    assert [bucket.is_under_ceiling for bucket in report.budget_buckets.buckets] == [False] * 5
    assert [bucket.plans for bucket in report.budget_buckets.buckets] == [()] * 5
    assert actions == ()
    assert message.paragraphs == (
        "0 of 8 customers bought on EMI. "
        "The biggest drop was after agreeing to a plan, before paying.",
    )
