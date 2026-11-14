"""Integration: the sale services on PostgreSQL with the Mock gateway and the composition bus."""

from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.api.dependencies import build_event_bus
from emi_copilot.core.qr_token_signer import QrTokenSigner
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType, EmiType
from emi_copilot.domain.sales import ChosenPlan, SaleStatus
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.services.customer_qr_link_issuer import CustomerQrLinkIssuer
from emi_copilot.services.list_counter_sales_service import ListCounterSalesService
from emi_copilot.services.mark_sale_ready_to_pay_service import (
    MarkSaleReadyToPayCommand,
    MarkSaleReadyToPayService,
)
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.sale_views import StartSaleCommand
from emi_copilot.services.start_sale_service import StartSaleService
from tests.fakes.lowest_free_session_code_generator import LowestFreeSessionCodeGenerator
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.merchant_builders import build_catalogue_product, build_merchant
from tests.sale_builders import PRODUCT_ID
from tests.unit.services.sale_service_wiring import PRINCIPAL

pytestmark = pytest.mark.integration

QR_SIGNING_KEY = b"synthetic-integration-qr-signing-key-0001"  # pragma: allowlist secret


@dataclass
class DatabaseSaleServices:
    """The sale services wired on the test database, and a reader of what they stored."""

    start_sale: StartSaleService
    list_counter_sales: ListCounterSalesService
    mark_ready_to_pay: MarkSaleReadyToPayService
    session_factory: sessionmaker[Session]
    clock: FixedClock

    def read_funnel_stages(self, sale_id: str) -> list[FunnelStage]:
        """Reads the stages one sale reached, oldest first, in a fresh transaction."""
        with SqlAlchemyUnitOfWork(self.session_factory, self.clock) as unit_of_work:
            return [event.stage for event in unit_of_work.funnel_events.list_for_sale(sale_id)]

    def read_sale_audit_types(self, sale_id: str) -> list[AuditEventType]:
        """Reads the audit types about one sale, oldest first."""
        with SqlAlchemyUnitOfWork(self.session_factory, self.clock) as unit_of_work:
            return [
                audit_event.event_type
                for audit_event in unit_of_work.audit_events.list_for_subject("sale", sale_id)
            ]


@pytest.fixture
def services(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> DatabaseSaleServices:
    """Stores the shop and its 128 GB phone, then wires the services as the root will."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.merchants.add(build_merchant())
        unit_of_work.products.add(
            build_catalogue_product(gateway_product_id=MOCK_PHONE_128_GB_PRODUCT_ID)
        )
    unit_of_work_factory = partial(SqlAlchemyUnitOfWork, session_factory, fixed_clock)
    event_bus = build_event_bus(SequentialIdGenerator("01JCEVENTROW"))
    expiry = SaleExpiryStep(event_bus, timedelta(hours=1))
    mock_gateway = MockPaymentGatewayAdapter(fixed_clock, b"integration-test-mock-signing-key-32b")
    return DatabaseSaleServices(
        start_sale=StartSaleService(
            unit_of_work_factory=unit_of_work_factory,
            clock=fixed_clock,
            id_generator=SequentialIdGenerator("01JCSALEROW"),
            event_bus=event_bus,
            session_code_generator=LowestFreeSessionCodeGenerator(),
            qr_link_issuer=CustomerQrLinkIssuer(
                QrTokenSigner(QR_SIGNING_KEY, fixed_clock),
                "https://customer.example.test",
                timedelta(minutes=15),
            ),
            sale_expiry=expiry,
        ),
        list_counter_sales=ListCounterSalesService(
            unit_of_work_factory, fixed_clock, expiry, ZoneInfo("Asia/Kolkata")
        ),
        mark_ready_to_pay=MarkSaleReadyToPayService(
            unit_of_work_factory,
            OfferDiscoveryService(mock_gateway, unit_of_work_factory, fixed_clock, event_bus),
            fixed_clock,
            event_bus,
            expiry,
        ),
        session_factory=session_factory,
        clock=fixed_clock,
    )


def test_start_then_agree_stores_the_mock_plan_and_both_funnel_rows(
    services: DatabaseSaleServices,
) -> None:
    """The Mock's card plan on ₹22,000 is frozen as shown; STARTED and AGREED are recorded."""
    sale_id = services.start_sale.start_sale(
        PRINCIPAL, StartSaleCommand(PRODUCT_ID)
    ).counter_sale.sale.id
    agreed_sale = services.mark_ready_to_pay.mark_ready_to_pay(
        MarkSaleReadyToPayCommand(sale_id=sale_id, offer_id="mock-offer-card-6m")
    )
    assert agreed_sale.status is SaleStatus.READY_TO_PAY
    assert agreed_sale.chosen_plan == ChosenPlan(
        offer_id="mock-offer-card-6m",
        plan_kind=EmiType.STANDARD,
        lender_label="Your card's bank",
        tenure_in_months=6,
        monthly_installment=Money.from_rupees("3850"),
        extra_in_total=Money.from_rupees("1100"),
        total_payable=Money.from_rupees("23100"),
    )
    assert services.read_funnel_stages(sale_id) == [FunnelStage.STARTED, FunnelStage.AGREED]
    assert services.read_sale_audit_types(sale_id) == [
        AuditEventType.SALE_STARTED,
        AuditEventType.SALE_STATUS_CHANGED,
    ]
    (listed_sale,) = services.list_counter_sales.list_counter_sales(PRINCIPAL)
    assert listed_sale.sale == agreed_sale


def test_open_sales_of_one_shop_get_different_session_codes(
    services: DatabaseSaleServices,
) -> None:
    """Three sales at the counter at once show three different codes."""
    session_codes = {
        services.start_sale.start_sale(
            PRINCIPAL, StartSaleCommand(PRODUCT_ID)
        ).counter_sale.sale.session_code.value
        for _ in range(3)
    }
    assert session_codes == {"0000", "0001", "0002"}


def test_counter_list_expires_an_unchosen_sale_at_exactly_one_hour_on_the_database(
    services: DatabaseSaleServices,
) -> None:
    """The stored row turns EXPIRED, dated at the deadline, and leaves the list."""
    started = services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID))
    services.clock.advance(timedelta(hours=1))
    assert services.list_counter_sales.list_counter_sales(PRINCIPAL) == ()
    with SqlAlchemyUnitOfWork(services.session_factory, services.clock) as unit_of_work:
        stored_sale = unit_of_work.sales.find_by_id_for_update(started.counter_sale.sale.id)
    assert stored_sale is not None
    assert stored_sale.status is SaleStatus.EXPIRED
    assert stored_sale.status_changed_at == started.counter_sale.sale.started_at + timedelta(
        hours=1
    )
