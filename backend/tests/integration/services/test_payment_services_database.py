"""Integration tests: payment services on PostgreSQL with the Mock gateway and the audit bus."""

from dataclasses import dataclass
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.domain.errors import (
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
    PaymentLinkCreationFailedError,
    PaymentLinkFailureCode,
)
from emi_copilot.domain.events import PaymentLinkCreated, WebhookOutcome
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    AuditEvent,
    AuditEventType,
    GatewayPaymentStatus,
    PaymentAttempt,
    PaymentAttemptStatus,
)
from emi_copilot.events.audit_subscriber import AuditSubscriber
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork
from emi_copilot.services.payment_handoff_service import PaymentHandoffService
from emi_copilot.services.payment_handoff_types import CreatePaymentLinkCommand
from emi_copilot.services.payment_status_service import PaymentStatusService
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock

pytestmark = pytest.mark.integration

MOCK_WEBHOOK_SIGNING_SECRET = b"integration-test-mock-signing-key-32b"
IDEMPOTENCY_KEY = "idempotency-key-integration-0001"


class SubscriberFailureError(Exception):
    """Stands in for any subscriber that fails after the audit row was written."""


@dataclass
class DatabaseServices:
    """The two payment services wired on the test database, and how to read what they stored."""

    handoff_service: PaymentHandoffService
    status_service: PaymentStatusService
    event_bus: DomainEventBus
    session_factory: sessionmaker[Session]
    clock: FixedClock

    def read_attempt(self) -> PaymentAttempt | None:
        """Reads the attempt stored under the test key, in a fresh transaction."""
        with SqlAlchemyUnitOfWork(self.session_factory, self.clock) as unit_of_work:
            return unit_of_work.payment_attempts.find_by_idempotency_key(IDEMPOTENCY_KEY)

    def read_audit_events(self, subject_id: str) -> list[AuditEvent]:
        """Reads every audit event about one payment attempt, oldest first."""
        with SqlAlchemyUnitOfWork(self.session_factory, self.clock) as unit_of_work:
            return list(unit_of_work.audit_events.list_for_subject("payment_attempt", subject_id))


def _wire_services(
    session_factory: sessionmaker[Session], clock: FixedClock, payment_gateway: PaymentGatewayPort
) -> DatabaseServices:
    """Wires both services as the composition root will, on the test database."""
    event_bus = DomainEventBus()
    AuditSubscriber(SequentialIdGenerator("01JCAUDITID"), lambda: None).subscribe_to(event_bus)
    id_generator = SequentialIdGenerator()

    def unit_of_work_factory() -> SqlAlchemyUnitOfWork:
        """Opens a real unit of work on the test database."""
        return SqlAlchemyUnitOfWork(session_factory, clock)

    return DatabaseServices(
        handoff_service=PaymentHandoffService(
            payment_gateway,
            unit_of_work_factory,
            clock,
            id_generator,
            event_bus,
            link_creation_stale_after=timedelta(seconds=26),
        ),
        status_service=PaymentStatusService(
            payment_gateway, unit_of_work_factory, clock, id_generator, event_bus
        ),
        event_bus=event_bus,
        session_factory=session_factory,
        clock=clock,
    )


@pytest.fixture
def mock_gateway(fixed_clock: FixedClock) -> MockPaymentGatewayAdapter:
    """Builds the labelled Mock gateway on the test clock."""
    return MockPaymentGatewayAdapter(fixed_clock, MOCK_WEBHOOK_SIGNING_SECRET)


@pytest.fixture
def services(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
) -> DatabaseServices:
    """Wires both services on the Mock gateway."""
    return _wire_services(session_factory, fixed_clock, mock_gateway)


def _build_command() -> CreatePaymentLinkCommand:
    """Asks for Mock plan B on a ₹22,000 item."""
    return CreatePaymentLinkCommand(
        idempotency_key=IDEMPOTENCY_KEY,
        offer_id="mock-offer-card-6m",
        price=Money.from_rupees("22000"),
        product_id="product-sample-0001",
        brand_id="brand-sample-0001",
        category_id="category-sample-0001",
    )


def _fail_after_the_audit_row(event: PaymentLinkCreated, unit_of_work: UnitOfWork) -> None:  # noqa: ARG001
    """Fails after the audit subscriber has written its row, as a database failure would."""
    raise SubscriberFailureError


def test_create_payment_link_stores_the_attempt_and_its_audit_row_together(
    services: DatabaseServices,
) -> None:
    """The LINK_CREATED attempt and its PAYMENT_LINK_CREATED row are both committed."""
    handoff = services.handoff_service.create_payment_link(_build_command())
    stored_attempt = services.read_attempt()
    assert stored_attempt is not None
    assert stored_attempt.status is PaymentAttemptStatus.LINK_CREATED
    assert stored_attempt.payment_link_url == handoff.payment_url
    assert stored_attempt.gateway_mode == "mock"
    assert [event.event_type for event in services.read_audit_events(stored_attempt.id)] == [
        AuditEventType.PAYMENT_LINK_CREATED
    ]


def test_create_payment_link_rolls_back_the_outcome_when_a_subscriber_fails(
    services: DatabaseServices,
) -> None:
    """A subscriber failure undoes LINK_CREATED and its audit row; the in-progress row stays."""
    services.event_bus.subscribe(PaymentLinkCreated, _fail_after_the_audit_row)
    with pytest.raises(SubscriberFailureError):
        services.handoff_service.create_payment_link(_build_command())
    stored_attempt = services.read_attempt()
    assert stored_attempt is not None
    assert stored_attempt.status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS
    assert stored_attempt.payment_link_url is None
    assert services.read_audit_events(stored_attempt.id) == []


def test_paid_webhook_after_an_unrecorded_link_moves_the_in_progress_attempt_to_paid(
    services: DatabaseServices, mock_gateway: MockPaymentGatewayAdapter
) -> None:
    """Recording LINK_CREATED fails, yet a later verified PAID webhook is applied and audited."""
    services.event_bus.subscribe(PaymentLinkCreated, _fail_after_the_audit_row)
    with pytest.raises(SubscriberFailureError):
        services.handoff_service.create_payment_link(_build_command())
    in_progress_attempt = services.read_attempt()
    assert in_progress_attempt is not None
    assert in_progress_attempt.status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS
    notification = mock_gateway.build_signed_notification(
        in_progress_attempt.order_id,
        GatewayPaymentStatus.PAID,
        "mock-transaction-0001",
        in_progress_attempt.amount,
    )
    application = services.status_service.apply_webhook(notification)
    assert (application.outcome, application.status) == (
        WebhookOutcome.STATUS_CHANGED,
        PaymentAttemptStatus.PAID,
    )
    paid_attempt = services.read_attempt()
    assert paid_attempt is not None
    assert paid_attempt.status is PaymentAttemptStatus.PAID
    audit_events = services.read_audit_events(paid_attempt.id)
    assert [event.event_type for event in audit_events] == [AuditEventType.PAYMENT_STATUS_CHANGED]
    assert audit_events[0].details["previous_status"] == "LINK_CREATION_IN_PROGRESS"


def test_create_payment_link_failure_code_is_stored_and_replayed(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """A refused link stores its code in failure_code, and a replay reads it back."""
    refusing_gateway = FakePaymentGateway(
        create_link_error=PaymentGatewayRequestRejectedError(
            PaymentGatewayRejectionReason.OPERATION_NOT_PERMITTED, "not allowed"
        )
    )
    services = _wire_services(session_factory, fixed_clock, refusing_gateway)
    command = CreatePaymentLinkCommand(
        idempotency_key=IDEMPOTENCY_KEY,
        offer_id="offer-plan-a",
        price=Money.from_rupees("22000"),
        product_id="product-sample-0001",
        brand_id="brand-sample-0001",
        category_id="category-sample-0001",
    )
    with pytest.raises(PaymentGatewayRequestRejectedError):
        services.handoff_service.create_payment_link(command)
    with pytest.raises(PaymentLinkCreationFailedError) as replay:
        services.handoff_service.create_payment_link(command)
    assert replay.value.failure_code is PaymentLinkFailureCode.OPERATION_NOT_PERMITTED
    stored_attempt = services.read_attempt()
    assert stored_attempt is not None
    assert stored_attempt.failure_code is PaymentLinkFailureCode.OPERATION_NOT_PERMITTED


def test_mock_webhook_marks_the_attempt_paid_once_and_a_repeat_adds_no_row(
    services: DatabaseServices, mock_gateway: MockPaymentGatewayAdapter
) -> None:
    """A signed Mock webhook is applied under a row lock; the identical repeat writes nothing."""
    handoff = services.handoff_service.create_payment_link(_build_command())
    notification = mock_gateway.build_signed_notification(
        handoff.order_id, GatewayPaymentStatus.PAID, "mock-transaction-0001", handoff.amount
    )
    first_application = services.status_service.apply_webhook(notification)
    audit_rows_after_first = services.read_audit_events(handoff.payment_attempt_id)
    repeated_application = services.status_service.apply_webhook(notification)
    assert first_application.outcome is WebhookOutcome.STATUS_CHANGED
    assert repeated_application.outcome is WebhookOutcome.NO_CHANGE
    assert services.read_audit_events(handoff.payment_attempt_id) == audit_rows_after_first
    assert [event.event_type for event in audit_rows_after_first] == [
        AuditEventType.PAYMENT_LINK_CREATED,
        AuditEventType.PAYMENT_STATUS_CHANGED,
    ]
    stored_attempt = services.read_attempt()
    assert stored_attempt is not None
    assert stored_attempt.status is PaymentAttemptStatus.PAID


def test_status_check_reads_the_mock_server_side_and_records_payment(
    services: DatabaseServices,
) -> None:
    """Pending until the Mock's delay passes, then PAID from a server-side check."""
    handoff = services.handoff_service.create_payment_link(_build_command())
    pending_view = services.status_service.get_payment_status(handoff.order_id)
    services.clock.advance(timedelta(seconds=30))
    paid_view = services.status_service.get_payment_status(handoff.order_id)
    assert pending_view.status is PaymentAttemptStatus.PAYMENT_PENDING
    assert (paid_view.status, paid_view.amount_paid) == (PaymentAttemptStatus.PAID, handoff.amount)
