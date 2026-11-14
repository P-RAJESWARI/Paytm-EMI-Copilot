"""MockCustomerSimulatorService: the customer's steps through the real services, own shop only."""

from datetime import timedelta

import pytest

from emi_copilot.adapters.payment_gateway.mock_payment_simulator_port import (
    MockPaymentSimulatorPort,
)
from emi_copilot.domain.errors import PaymentAttemptNotFoundError, SaleNotFoundError
from emi_copilot.domain.events import WebhookOutcome
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    GatewayPaymentStatus,
    PaymentAttemptStatus,
    UnverifiedWebhookNotification,
    VerifiedWebhookEvent,
)
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.services.mark_sale_ready_to_pay_service import MarkSaleReadyToPayService
from emi_copilot.services.mock_customer_simulator_service import MockCustomerSimulatorService
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.payment_status_service import PaymentStatusService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from tests.fakes.fake_payment_gateway import build_signed_notification
from tests.merchant_builders import build_catalogue_product
from tests.payment_builders import build_payment_attempt
from tests.sale_builders import SALE_ID, build_sale
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.sale_service_wiring import CHOOSING_LIFETIME, OTHER_PRINCIPAL, PRINCIPAL

PAID_SIGNATURE = "signature-simulated-paid"
SALE_ORDER_ID = "ORDER-SAMPLE-0001"


class RecordingMockPaymentSimulator(MockPaymentSimulatorPort):
    """Stands in for the Mock gateway's customer controls and remembers which orders it paid."""

    def __init__(self) -> None:
        """Starts with no paid orders."""
        self.paid_order_ids: list[str] = []

    def complete_mock_payment(self, order_id: str) -> UnverifiedWebhookNotification:
        """Records the order and gives the fake gateway's signed notification."""
        self.paid_order_ids.append(order_id)
        return build_signed_notification(PAID_SIGNATURE)


def _build_service(
    kit: ServiceTestKit, simulator: RecordingMockPaymentSimulator
) -> MockCustomerSimulatorService:
    """Wires the simulator on the services the real flow uses, all on the kit's fakes."""
    return MockCustomerSimulatorService(
        kit.unit_of_work_factory,
        MarkSaleReadyToPayService(
            kit.unit_of_work_factory,
            OfferDiscoveryService(
                kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.event_bus
            ),
            kit.clock,
            kit.event_bus,
            SaleExpiryStep(kit.event_bus, CHOOSING_LIFETIME),
        ),
        PaymentStatusService(
            kit.payment_gateway,
            kit.unit_of_work_factory,
            kit.clock,
            kit.id_generator,
            kit.event_bus,
        ),
        simulator,
    )


def _store_sale(kit: ServiceTestKit, status: SaleStatus) -> None:
    """Stores the shop's product and its sale in the given status."""
    product = build_catalogue_product()
    kit.database.products_by_id[product.id] = product
    kit.database.sales_by_id[SALE_ID] = build_sale(status=status)


def test_agree_to_plan_moves_the_shops_choosing_sale_to_ready_to_pay(
    kit: ServiceTestKit,
) -> None:
    """The agreed offer is re-quoted and frozen by MarkSaleReadyToPayService."""
    _store_sale(kit, SaleStatus.CHOOSING)
    counter_sale = _build_service(kit, RecordingMockPaymentSimulator()).agree_to_plan(
        PRINCIPAL, SALE_ID, "offer-plan-b"
    )
    assert counter_sale.sale.status is SaleStatus.READY_TO_PAY
    assert counter_sale.sale.chosen_plan is not None
    assert counter_sale.sale.chosen_plan.offer_id == "offer-plan-b"
    assert counter_sale.product_name == build_catalogue_product().name


def test_agree_to_plan_on_another_shops_sale_is_not_found_and_changes_nothing(
    kit: ServiceTestKit,
) -> None:
    """The simulator checks the shop before it plays the customer."""
    _store_sale(kit, SaleStatus.CHOOSING)
    with pytest.raises(SaleNotFoundError):
        _build_service(kit, RecordingMockPaymentSimulator()).agree_to_plan(
            OTHER_PRINCIPAL, SALE_ID, "offer-plan-b"
        )
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.CHOOSING
    assert kit.payment_gateway.discover_offers_calls == []


def test_complete_payment_hands_the_signed_report_to_the_webhook_path(
    kit: ServiceTestKit,
) -> None:
    """The report is verified like any webhook, then moves the attempt and the sale to PAID."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    kit.store_attempt(
        build_payment_attempt(
            status=PaymentAttemptStatus.LINK_CREATED,
            gateway_link_id="link-0001",
            payment_link_url="https://fake-gateway.invalid/pay/link-0001",
            sale_id=SALE_ID,
        )
    )
    kit.payment_gateway.verified_events_by_signature[PAID_SIGNATURE] = VerifiedWebhookEvent(
        order_id=SALE_ORDER_ID,
        status=GatewayPaymentStatus.PAID,
        gateway_transaction_id="transaction-0001",
        amount_paid=Money.from_rupees("22000"),
    )
    simulator = RecordingMockPaymentSimulator()
    kit.clock.advance(timedelta(minutes=1))
    application = _build_service(kit, simulator).complete_payment(PRINCIPAL, SALE_ORDER_ID)
    assert simulator.paid_order_ids == [SALE_ORDER_ID]
    assert application.outcome is WebhookOutcome.STATUS_CHANGED
    assert kit.only_attempt().status is PaymentAttemptStatus.PAID
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.PAID


@pytest.mark.parametrize("is_linked_to_the_sale", [True, False])
def test_complete_payment_of_another_shops_or_a_sale_less_payment_is_not_found(
    kit: ServiceTestKit, *, is_linked_to_the_sale: bool
) -> None:
    """Only the shop's own sale payments can be paid; nothing reaches the Mock otherwise."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    kit.store_attempt(build_payment_attempt(sale_id=SALE_ID if is_linked_to_the_sale else None))
    simulator = RecordingMockPaymentSimulator()
    principal = OTHER_PRINCIPAL if is_linked_to_the_sale else PRINCIPAL
    with pytest.raises(PaymentAttemptNotFoundError):
        _build_service(kit, simulator).complete_payment(principal, SALE_ORDER_ID)
    assert simulator.paid_order_ids == []
