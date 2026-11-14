"""DemoReportHistorySeedService on fakes: placement in the week, plan choice, written once."""

from datetime import UTC, datetime, timedelta

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.services.demo_report_history_seed_service import (
    DemoReportHistorySeedService,
    HistoryOutcome,
    HistorySale,
    choose_plan_within_budget,
    schedule_history_moments,
)
from tests.merchant_builders import build_merchant
from tests.report_builders import build_phone_128_gb_offers
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.report_service_wiring import SyntheticWeek
from tests.unit.services.sale_service_wiring import CHOOSING_LIFETIME, INDIA_TIME_ZONE

SATURDAY_AFTERNOON = datetime(2026, 11, 14, 10, 30, tzinfo=UTC)
MONDAY_NOON = datetime(2026, 11, 16, 6, 30, tzinfo=UTC)
MONDAY_JUST_AFTER_MIDNIGHT = datetime(2026, 11, 15, 18, 40, tzinfo=UTC)
WEEK_START = datetime(2026, 11, 8, 18, 30, tzinfo=UTC)
GATEWAY_PRODUCT_128 = "mock-product-phone-128gb"
SMALL_HISTORY = (
    HistorySale(GATEWAY_PRODUCT_128, FunnelStage.PLANS_VIEWED, "2400", HistoryOutcome.EXPIRED),
    HistorySale(GATEWAY_PRODUCT_128, FunnelStage.PAID, "3200", HistoryOutcome.PAID),
    HistorySale(
        GATEWAY_PRODUCT_128, FunnelStage.AGREED, "5000", HistoryOutcome.PAYMENT_NOT_COMPLETED
    ),
    HistorySale(
        GATEWAY_PRODUCT_128, FunnelStage.AGREED, "4000", HistoryOutcome.READY_TO_PAY, "4817", 12
    ),
    HistorySale(GATEWAY_PRODUCT_128, FunnelStage.STARTED, None, HistoryOutcome.CHOOSING, "4821", 3),
)


def test_history_on_a_saturday_falls_on_monday_to_friday_from_ten_in_the_morning() -> None:
    """Earlier days of the week, round-robin, so today's counter list stays short."""
    moments = schedule_history_moments(10, SATURDAY_AFTERNOON, INDIA_TIME_ZONE)
    local_dates = {moment.date().isoformat() for moment in moments}
    assert local_dates == {"2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"}
    assert moments[0] == datetime(2026, 11, 9, 10, 0, tzinfo=INDIA_TIME_ZONE)
    assert moments[5] == datetime(2026, 11, 9, 10, 7, tzinfo=INDIA_TIME_ZONE)


def test_history_on_a_monday_falls_earlier_today_before_a_margin() -> None:
    """No earlier day exists, so the sales spread between midnight and 90 minutes ago."""
    moments = schedule_history_moments(4, MONDAY_NOON, INDIA_TIME_ZONE)
    assert moments[0] == datetime(2026, 11, 16, 0, 0, tzinfo=INDIA_TIME_ZONE)
    assert all(moment <= MONDAY_NOON - timedelta(minutes=90) for moment in moments)


def test_history_just_after_monday_midnight_stays_at_the_week_start() -> None:
    """Too early for any spread: every sale starts at Monday 00:00, still this week."""
    moments = schedule_history_moments(3, MONDAY_JUST_AFTER_MIDNIGHT, INDIA_TIME_ZONE)
    assert {moment.astimezone(UTC) for moment in moments} == {
        datetime(2026, 11, 15, 18, 30, tzinfo=UTC)
    }
    assert schedule_history_moments(0, MONDAY_NOON, INDIA_TIME_ZONE) == []


@pytest.mark.parametrize(
    ("budget_in_rupees", "expected_plan_kind", "expected_monthly_in_rupees"),
    [
        ("4500", EmiType.NO_COST, "3666.67"),
        ("3200", EmiType.STANDARD, "2050"),
        ("1000", EmiType.NO_COST, "3666.67"),
        (None, EmiType.NO_COST, "3666.67"),
    ],
)
def test_choose_plan_within_budget_picks_the_least_extra_that_fits(
    budget_in_rupees: str | None, expected_plan_kind: EmiType, expected_monthly_in_rupees: str
) -> None:
    """No-cost when it fits, else the cheapest monthly that fits; nothing fits: lowest extra."""
    budget = None if budget_in_rupees is None else Money.from_rupees(budget_in_rupees)
    plan = choose_plan_within_budget(build_phone_128_gb_offers(), budget)
    assert (plan.plan_kind, plan.monthly_installment) == (
        expected_plan_kind,
        Money.from_rupees(expected_monthly_in_rupees),
    )


def _build_service(kit: ServiceTestKit) -> DemoReportHistorySeedService:
    """Wires the seed on the fakes and the Mock gateway's demo plans."""
    return DemoReportHistorySeedService(
        unit_of_work_factory=kit.unit_of_work_factory,
        payment_gateway=MockPaymentGatewayAdapter(kit.clock, b"seed-history-test-mock-signing-key"),
        clock=kit.clock,
        id_generator=kit.id_generator,
        time_zone=INDIA_TIME_ZONE,
        choosing_lifetime=CHOOSING_LIFETIME,
    )


def test_seed_writes_each_sale_through_the_state_machine_once(kit: ServiceTestKit) -> None:
    """Statuses, stages and budgets as specified; a second run writes nothing."""
    merchant = build_merchant(shop_code="RAVI-0193")
    kit.database.merchants_by_id[merchant.id] = merchant
    SyntheticWeek(kit)
    service = _build_service(kit)
    first = service.seed("RAVI-0193", SMALL_HISTORY)
    second = service.seed("RAVI-0193", SMALL_HISTORY)
    sales = [sale for sale in kit.database.sales_by_id.values() if sale.merchant_id == merchant.id]
    assert (first.added_sale_count, second.added_sale_count) == (5, 0)
    assert sorted(sale.status.value for sale in sales) == sorted(
        status.value
        for status in (
            SaleStatus.EXPIRED,
            SaleStatus.PAID,
            SaleStatus.PAYMENT_NOT_COMPLETED,
            SaleStatus.READY_TO_PAY,
            SaleStatus.CHOOSING,
        )
    )
    assert len(kit.database.funnel_events) == 3 + 5 + 4 + 4 + 1
    ready_sale = next(sale for sale in sales if sale.session_code.value == "4817")
    assert ready_sale.started_at == SATURDAY_AFTERNOON + timedelta(microseconds=123456) - timedelta(
        minutes=12
    )
    assert all(WEEK_START <= sale.started_at <= kit.clock.now() for sale in sales)


def test_seed_needs_the_shop_to_exist(kit: ServiceTestKit) -> None:
    """The shop step runs first; without it nothing is guessed."""
    with pytest.raises(InvalidMerchantDataError, match="demo shop"):
        _build_service(kit).seed("RAVI-0193", SMALL_HISTORY)
