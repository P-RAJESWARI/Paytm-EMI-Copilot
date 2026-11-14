"""Integration: a verified webhook moves the attempt's sale on PostgreSQL, in one transaction."""

from functools import partial

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.api.dependencies import build_event_bus
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    AuditEventType,
    GatewayPaymentStatus,
    PaymentAttemptStatus,
    VerifiedWebhookEvent,
)
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.services.payment_status_service import PaymentStatusService
from tests.fakes.fake_payment_gateway import FakePaymentGateway, build_signed_notification
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.merchant_builders import build_catalogue_product, build_merchant
from tests.payment_builders import build_payment_attempt
from tests.sale_builders import SALE_ID, build_sale

pytestmark = pytest.mark.integration

SIGNATURE = "signature-paid-0001"


def store_ready_to_pay_sale_with_attempt(
    session_factory: sessionmaker[Session], clock: FixedClock, *, is_linked_to_sale: bool
) -> str:
    """Commits a READY_TO_PAY sale and a LINK_CREATED attempt; gives the attempt's order id."""
    attempt = build_payment_attempt(
        1,
        status=PaymentAttemptStatus.LINK_CREATED,
        gateway_link_id="link-0001",
        payment_link_url="https://mock-payments.invalid/pay/link-0001",
        sale_id=SALE_ID if is_linked_to_sale else None,
    )
    with SqlAlchemyUnitOfWork(session_factory, clock) as unit_of_work:
        unit_of_work.merchants.add(build_merchant())
        unit_of_work.products.add(build_catalogue_product())
        unit_of_work.sales.add(build_sale(status=SaleStatus.READY_TO_PAY))
        unit_of_work.payment_attempts.add(attempt)
    return attempt.order_id


def apply_paid_webhook(
    session_factory: sessionmaker[Session], clock: FixedClock, order_id: str
) -> None:
    """Applies a verified PAID webhook through the status service on the composition bus."""
    gateway = FakePaymentGateway()
    gateway.verified_events_by_signature[SIGNATURE] = VerifiedWebhookEvent(
        order_id=order_id,
        status=GatewayPaymentStatus.PAID,
        gateway_transaction_id="transaction-0001",
        amount_paid=Money.from_rupees("22000"),
    )
    status_service = PaymentStatusService(
        gateway,
        partial(SqlAlchemyUnitOfWork, session_factory, clock),
        clock,
        SequentialIdGenerator("01JCDELIVERY"),
        build_event_bus(SequentialIdGenerator()),
    )
    status_service.apply_webhook(build_signed_notification(SIGNATURE))


def test_paid_webhook_marks_the_sale_paid_with_its_funnel_row_and_audits(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Attempt PAID, sale PAID, a PAID funnel row and both audit rows commit together."""
    order_id = store_ready_to_pay_sale_with_attempt(
        session_factory, fixed_clock, is_linked_to_sale=True
    )
    apply_paid_webhook(session_factory, fixed_clock, order_id)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        sale = unit_of_work.sales.find_by_id_for_update(SALE_ID)
        funnel_stages = [event.stage for event in unit_of_work.funnel_events.list_for_sale(SALE_ID)]
        sale_audit_types = [
            audit_event.event_type
            for audit_event in unit_of_work.audit_events.list_for_subject("sale", SALE_ID)
        ]
    assert sale is not None
    assert sale.status is SaleStatus.PAID
    assert funnel_stages == [FunnelStage.PAID]
    assert sale_audit_types == [AuditEventType.SALE_STATUS_CHANGED]


def test_paid_webhook_for_an_attempt_without_a_sale_leaves_every_sale_alone(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Layer 1 hand-offs keep working exactly as before."""
    order_id = store_ready_to_pay_sale_with_attempt(
        session_factory, fixed_clock, is_linked_to_sale=False
    )
    apply_paid_webhook(session_factory, fixed_clock, order_id)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        sale = unit_of_work.sales.find_by_id_for_update(SALE_ID)
        attempt = unit_of_work.payment_attempts.find_by_order_id(order_id)
    assert sale is not None
    assert sale.status is SaleStatus.READY_TO_PAY
    assert attempt is not None
    assert attempt.status is PaymentAttemptStatus.PAID
