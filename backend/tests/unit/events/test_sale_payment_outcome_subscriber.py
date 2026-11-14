"""SalePaymentOutcomeSubscriber: a PAID or FAILED report moves the attempt's sale, tolerantly."""

from dataclasses import replace
from datetime import timedelta

import pytest

from emi_copilot.domain.errors import PaymentAttemptNotFoundError, SaleNotFoundError
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.payments import AuditEventType, PaymentAttemptStatus
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.events.audit_subscriber import AuditSubscriber
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.events.funnel_event_recorder import FunnelEventRecorder
from emi_copilot.events.sale_payment_outcome_subscriber import SalePaymentOutcomeSubscriber
from tests.event_builders import build_payment_status_changed
from tests.fakes.fake_unit_of_work import FakeUnitOfWorkFactory, InMemoryDatabase
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT, build_payment_attempt
from tests.sale_builders import SALE_ID, build_sale

Attempt = PaymentAttemptStatus
REPORTED_AT = build_payment_status_changed().occurred_at


@pytest.fixture
def database() -> InMemoryDatabase:
    """An empty in-memory database shared by the test's units of work."""
    return InMemoryDatabase()


@pytest.fixture
def event_bus() -> DomainEventBus:
    """A bus wired like the composition root: audit, funnel, then the sale payment rules."""
    bus = DomainEventBus()
    AuditSubscriber(SequentialIdGenerator("01JCAUDITID"), lambda: None).subscribe_to(bus)
    FunnelEventRecorder(SequentialIdGenerator("01JCFUNNELID")).subscribe_to(bus)
    SalePaymentOutcomeSubscriber(bus).subscribe()
    return bus


def store(database: InMemoryDatabase, sale_status: SaleStatus, *, has_sale: bool = True) -> None:
    """Stores a sale in the given status and the sample attempt, linked to it or not."""
    database.sales_by_id[SALE_ID] = build_sale(status=sale_status)
    attempt = build_payment_attempt(1, sale_id=SALE_ID if has_sale else None)
    database.payment_attempts_by_id[attempt.id] = attempt


def report(
    event_bus: DomainEventBus, database: InMemoryDatabase, new_status: PaymentAttemptStatus
) -> None:
    """Publishes one attempt status change in a fake unit of work, as PaymentStatusService does."""
    with FakeUnitOfWorkFactory(database, FixedClock(CREATED_AT))() as unit_of_work:
        event_bus.publish(build_payment_status_changed(new_status=new_status), unit_of_work)


def audit_types(database: InMemoryDatabase) -> list[AuditEventType]:
    """Lists the committed audit types, oldest first."""
    return [audit_event.event_type for audit_event in database.audit_events]


@pytest.mark.parametrize(
    ("moves", "expected_stages"),
    [
        ((SaleStatus.READY_TO_PAY, Attempt.PAID, SaleStatus.PAID), [FunnelStage.PAID]),
        (
            (SaleStatus.READY_TO_PAY, Attempt.PAYMENT_FAILED, SaleStatus.PAYMENT_NOT_COMPLETED),
            [],
        ),
        ((SaleStatus.PAYMENT_NOT_COMPLETED, Attempt.PAID, SaleStatus.PAID), [FunnelStage.PAID]),
    ],
)
def test_paid_and_failed_reports_move_the_sale_and_are_audited(
    event_bus: DomainEventBus,
    database: InMemoryDatabase,
    moves: tuple[SaleStatus, PaymentAttemptStatus, SaleStatus],
    expected_stages: list[FunnelStage],
) -> None:
    """The sale follows the gateway's confirmed report at the report's moment."""
    sale_status, attempt_status, expected_sale_status = moves
    store(database, sale_status)
    report(event_bus, database, attempt_status)
    sale = database.sales_by_id[SALE_ID]
    assert (sale.status, sale.status_changed_at) == (expected_sale_status, REPORTED_AT)
    assert audit_types(database) == [
        AuditEventType.PAYMENT_STATUS_CHANGED,
        AuditEventType.SALE_STATUS_CHANGED,
    ]
    assert database.audit_events[1].details["payment_attempt_id"] == build_payment_attempt().id
    assert [funnel_event.stage for funnel_event in database.funnel_events] == expected_stages


@pytest.mark.parametrize("attempt_status", [Attempt.PAID, Attempt.PAYMENT_FAILED])
def test_repeated_or_late_report_on_a_paid_sale_changes_nothing(
    event_bus: DomainEventBus, database: InMemoryDatabase, attempt_status: PaymentAttemptStatus
) -> None:
    """PAID is final; the report is audited as an attempt change only."""
    store(database, SaleStatus.PAID)
    report(event_bus, database, attempt_status)
    assert database.sales_by_id[SALE_ID] == build_sale(status=SaleStatus.PAID)
    assert audit_types(database) == [AuditEventType.PAYMENT_STATUS_CHANGED]


@pytest.mark.parametrize("sale_status", [SaleStatus.CHOOSING, SaleStatus.EXPIRED])
def test_report_on_a_sale_not_awaiting_payment_is_ignored_and_audited(
    event_bus: DomainEventBus, database: InMemoryDatabase, sale_status: SaleStatus
) -> None:
    """No plan was agreed, so nothing moves, nothing raises, and the oddity is on record."""
    store(database, sale_status)
    report(event_bus, database, Attempt.PAID)
    assert database.sales_by_id[SALE_ID].status is sale_status
    assert audit_types(database) == [
        AuditEventType.PAYMENT_STATUS_CHANGED,
        AuditEventType.SALE_PAYMENT_OUTCOME_IGNORED,
    ]
    assert database.audit_events[1].details["sale_status"] == sale_status.value
    assert database.audit_events[1].details["ignored_reason"] == "SALE_NOT_AWAITING_PAYMENT"


def store_replacement_attempt(database: InMemoryDatabase) -> None:
    """Stores a newer attempt for the sale, as a new key does after the first proved linkless."""
    created_at = CREATED_AT + timedelta(minutes=5)
    newer_attempt = build_payment_attempt(
        2, sale_id=SALE_ID, created_at=created_at, updated_at=created_at
    )
    database.payment_attempts_by_id[newer_attempt.id] = newer_attempt


def test_failed_report_on_a_replaced_attempt_leaves_the_new_link_live_and_is_audited(
    event_bus: DomainEventBus, database: InMemoryDatabase
) -> None:
    """A late FAILED on the old attempt must not move READY_TO_PAY while the new link is live."""
    store(database, SaleStatus.READY_TO_PAY)
    store_replacement_attempt(database)
    report(event_bus, database, Attempt.PAYMENT_FAILED)
    assert database.sales_by_id[SALE_ID] == build_sale(status=SaleStatus.READY_TO_PAY)
    assert audit_types(database) == [
        AuditEventType.PAYMENT_STATUS_CHANGED,
        AuditEventType.SALE_PAYMENT_OUTCOME_IGNORED,
    ]
    assert database.audit_events[1].details == {
        "merchant_id": build_sale().merchant_id,
        "sale_status": "READY_TO_PAY",
        "payment_outcome": "NOT_COMPLETED",
        "payment_attempt_id": build_payment_attempt().id,
        "ignored_reason": "ATTEMPT_REPLACED",
    }


def test_paid_report_on_a_replaced_attempt_still_pays_the_sale(
    event_bus: DomainEventBus, database: InMemoryDatabase
) -> None:
    """The customer paid on the old link: the money was taken, so the sale is PAID."""
    store(database, SaleStatus.READY_TO_PAY)
    store_replacement_attempt(database)
    report(event_bus, database, Attempt.PAID)
    assert database.sales_by_id[SALE_ID].status is SaleStatus.PAID
    assert audit_types(database) == [
        AuditEventType.PAYMENT_STATUS_CHANGED,
        AuditEventType.SALE_STATUS_CHANGED,
    ]


def test_pending_report_settles_nothing(
    event_bus: DomainEventBus, database: InMemoryDatabase
) -> None:
    """A pending payment leaves the sale READY_TO_PAY."""
    store(database, SaleStatus.READY_TO_PAY)
    report(event_bus, database, Attempt.PAYMENT_PENDING)
    assert database.sales_by_id[SALE_ID].status is SaleStatus.READY_TO_PAY


def test_attempt_without_a_sale_is_ignored(
    event_bus: DomainEventBus, database: InMemoryDatabase
) -> None:
    """Layer 1 callers hand off a bare item; their attempts move no sale."""
    store(database, SaleStatus.READY_TO_PAY, has_sale=False)
    report(event_bus, database, Attempt.PAID)
    assert database.sales_by_id[SALE_ID].status is SaleStatus.READY_TO_PAY
    assert audit_types(database) == [AuditEventType.PAYMENT_STATUS_CHANGED]


def test_report_for_an_unknown_attempt_raises(
    event_bus: DomainEventBus, database: InMemoryDatabase
) -> None:
    """The publisher just saved the attempt, so its absence is a bug, not a no-op."""
    with pytest.raises(PaymentAttemptNotFoundError):
        report(event_bus, database, Attempt.PAID)


def test_attempt_pointing_at_a_missing_sale_raises(
    event_bus: DomainEventBus, database: InMemoryDatabase
) -> None:
    """The foreign key makes this impossible in PostgreSQL; the fake proves the guard."""
    store(database, SaleStatus.READY_TO_PAY)
    database.sales_by_id.clear()
    attempt = build_payment_attempt(1)
    database.payment_attempts_by_id[attempt.id] = replace(attempt, sale_id=SALE_ID)
    with pytest.raises(SaleNotFoundError):
        report(event_bus, database, Attempt.PAID)
