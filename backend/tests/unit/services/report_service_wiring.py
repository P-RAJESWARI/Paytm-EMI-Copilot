"""Wires the report services on the service-test fakes and a small synthetic week of sales."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_EARBUDS_PRODUCT_ID,
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.adapters.settlement.mock_adapter import MockSettlementAdapter
from emi_copilot.adapters.weekly_message_delivery.port import WeeklyMessageDeliveryPort
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.small_count_suppression import SmallCountSuppressionPolicy
from emi_copilot.domain.reports.weekly_message_record import WeeklyMessageDelivery
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageTemplate
from emi_copilot.domain.sales import SaleStatus, SessionCode
from emi_copilot.services.missed_sales_analyser import MissedSalesAnalyser
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.report_periods import ReportPeriods
from emi_copilot.services.report_services import (
    FunnelReportService,
    MissedSalesReportService,
    MoneyDueReportService,
    SuggestedActionsService,
)
from emi_copilot.services.weekly_message_service import (
    WeeklyMessageReports,
    WeeklyMessageService,
)
from tests.merchant_builders import OTHER_MERCHANT_ID, build_catalogue_product
from tests.sale_builders import build_sale
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.sale_service_wiring import INDIA_TIME_ZONE

PHONE_128_GB_ID = "01JCPRODUCT000000000000128"
PHONE_64_GB_ID = "01JCPRODUCT000000000000064"
EARBUDS_ID = "01JCPRODUCT000000000000003"
OTHER_SHOP_PRODUCT_ID = "01JCPRODUCT000000000000999"
MOCK_SIGNING_SECRET = b"report-service-test-mock-signing-key"
STAGES_THROUGH = {
    FunnelStage.STARTED: 1,
    FunnelStage.BUDGET_TOLD: 2,
    FunnelStage.PLANS_VIEWED: 3,
    FunnelStage.AGREED: 4,
}
FUNNEL_ORDER = (
    FunnelStage.STARTED,
    FunnelStage.BUDGET_TOLD,
    FunnelStage.PLANS_VIEWED,
    FunnelStage.AGREED,
)


@dataclass
class RecordingDelivery(WeeklyMessageDeliveryPort):
    """A delivery port that remembers what it was asked to send."""

    deliveries: list[WeeklyMessageDelivery] = field(default_factory=list)

    @property
    def adapter_name(self) -> str:
        """Gives "recording"."""
        return "recording"

    def deliver_weekly_message(self, delivery: WeeklyMessageDelivery) -> None:
        """Records the delivery."""
        self.deliveries.append(delivery)


@dataclass
class ReportServices:
    """Every report service on one kit, plus the recording delivery port."""

    funnel: FunnelReportService
    missed_sales: MissedSalesReportService
    suggested_actions: SuggestedActionsService
    money_due: MoneyDueReportService
    weekly_message: WeeklyMessageService
    delivery: RecordingDelivery


def build_report_services(kit: ServiceTestKit) -> ReportServices:
    """Wires the services as the composition root does, on the Mock gateway's demo plans."""
    gateway = MockPaymentGatewayAdapter(kit.clock, MOCK_SIGNING_SECRET)
    policy = SmallCountSuppressionPolicy()
    periods = ReportPeriods(kit.clock, INDIA_TIME_ZONE)
    analyser = MissedSalesAnalyser(
        kit.unit_of_work_factory,
        OfferDiscoveryService(gateway, kit.unit_of_work_factory, kit.clock, kit.event_bus),
    )
    funnel = FunnelReportService(kit.unit_of_work_factory, periods, policy)
    missed_sales = MissedSalesReportService(analyser, periods, policy)
    suggested_actions = SuggestedActionsService(analyser, periods, policy)
    money_due = MoneyDueReportService(MockSettlementAdapter())
    delivery = RecordingDelivery()
    weekly_message = WeeklyMessageService(
        unit_of_work_factory=kit.unit_of_work_factory,
        clock=kit.clock,
        id_generator=kit.id_generator,
        report_periods=periods,
        reports=WeeklyMessageReports(funnel, missed_sales, suggested_actions, money_due),
        template=WeeklyMessageTemplate(format_paise_as_whole_rupees),
        delivery=delivery,
    )
    return ReportServices(
        funnel, missed_sales, suggested_actions, money_due, weekly_message, delivery
    )


class SyntheticWeek:
    """Stores the shop's three demo products and sales that reached chosen stages."""

    def __init__(self, kit: ServiceTestKit) -> None:
        """Stores the products of both shops."""
        self._kit = kit
        self._sale_number = 0
        for product in (
            build_catalogue_product(
                id=PHONE_128_GB_ID, gateway_product_id=MOCK_PHONE_128_GB_PRODUCT_ID
            ),
            build_catalogue_product(
                id=PHONE_64_GB_ID,
                name="Example phone, 64 GB",
                list_price=Money.from_rupees("18000"),
                gateway_product_id=MOCK_PHONE_64_GB_PRODUCT_ID,
            ),
            build_catalogue_product(
                id=EARBUDS_ID,
                name="Example earbuds",
                list_price=Money.from_rupees("2499"),
                gateway_product_id=MOCK_EARBUDS_PRODUCT_ID,
            ),
            build_catalogue_product(
                id=OTHER_SHOP_PRODUCT_ID,
                merchant_id=OTHER_MERCHANT_ID,
                gateway_product_id=MOCK_PHONE_128_GB_PRODUCT_ID,
            ),
        ):
            kit.database.products_by_id[product.id] = product

    def store_sale(
        self,
        last_stage: FunnelStage,
        budget_in_rupees: str = "4000",
        *,
        product_id: str = PHONE_128_GB_ID,
        started_at: datetime | None = None,
    ) -> None:
        """Stores one sale that reached every stage up to last_stage, budget on BUDGET_TOLD."""
        self._sale_number += 1
        moment = started_at or self._kit.clock.now() - timedelta(hours=self._sale_number)
        product = self._kit.database.products_by_id[product_id]
        sale_id = f"01JCWEEKSALE{self._sale_number:014d}"
        has_agreed = last_stage is FunnelStage.AGREED
        self._kit.database.sales_by_id[sale_id] = build_sale(
            id=sale_id,
            merchant_id=product.merchant_id,
            product_id=product_id,
            price=Money.from_rupees("22000"),
            session_code=SessionCode(f"{self._sale_number:04d}"),
            status=SaleStatus.PAID if has_agreed else SaleStatus.EXPIRED,
            started_at=moment,
            status_changed_at=moment,
        )
        for stage in FUNNEL_ORDER[: STAGES_THROUGH[last_stage]]:
            self._kit.database.funnel_events.append(
                FunnelEvent(
                    id=f"01JCWEEKEVENT{self._sale_number:05d}{stage.value}",
                    sale_id=sale_id,
                    merchant_id=product.merchant_id,
                    stage=stage,
                    occurred_at=moment,
                    monthly_budget=(
                        Money.from_rupees(budget_in_rupees)
                        if stage is FunnelStage.BUDGET_TOLD
                        else None
                    ),
                )
            )


def store_synthetic_week(kit: ServiceTestKit) -> None:
    """Six missed on the 128 GB phone (₹2,400 to ₹2,950), two agreed, one 64 GB not missed.

    Plus one missed sale of another shop and one of last week, which no report may count.
    """
    week = SyntheticWeek(kit)
    for budget_in_rupees in ("2400", "2600", "2700", "2800", "2900", "2950"):
        week.store_sale(FunnelStage.PLANS_VIEWED, budget_in_rupees)
    week.store_sale(FunnelStage.AGREED, "3200")
    week.store_sale(FunnelStage.AGREED, "3200")
    week.store_sale(FunnelStage.PLANS_VIEWED, "3100", product_id=PHONE_64_GB_ID)
    week.store_sale(FunnelStage.PLANS_VIEWED, "1000", product_id=OTHER_SHOP_PRODUCT_ID)
    week.store_sale(
        FunnelStage.PLANS_VIEWED, "1000", started_at=kit.clock.now() - timedelta(days=7)
    )
