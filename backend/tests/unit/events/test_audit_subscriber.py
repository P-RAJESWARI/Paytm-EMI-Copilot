"""Tests for AuditSubscriber: one audit row per event, with ids, codes and paise only."""

import pytest

from emi_copilot.core.request_context import correlation_id_context
from emi_copilot.domain.events import DomainEvent
from emi_copilot.domain.payments import AuditEvent, AuditEventType
from emi_copilot.events.audit_subscriber import AUDIT_MAPPINGS_BY_EVENT_TYPE, AuditSubscriber
from emi_copilot.events.event_bus import DomainEventBus
from tests.event_builders import (
    SAMPLE_ATTEMPT_ID,
    build_every_domain_event,
    build_payment_status_changed,
)
from tests.fakes.fake_unit_of_work import FakeUnitOfWorkFactory, InMemoryDatabase
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT

SAMPLE_CORRELATION_ID = "correlation-sample-0001"


class SimulatedUseCaseFailureError(Exception):
    """Stands in for any error the publishing service raises after publishing."""


def _publish_then_fail(
    event_bus: DomainEventBus, unit_of_work_factory: FakeUnitOfWorkFactory
) -> None:
    """Publishes one event in a unit of work, then fails before the unit can commit."""
    with unit_of_work_factory() as unit_of_work:
        event_bus.publish(build_payment_status_changed(), unit_of_work)
        raise SimulatedUseCaseFailureError


@pytest.fixture
def unit_of_work_factory() -> FakeUnitOfWorkFactory:
    """Gives fake units of work on one shared in-memory database."""
    return FakeUnitOfWorkFactory(InMemoryDatabase(), FixedClock(CREATED_AT))


def _publish_through_audit(
    events: list[DomainEvent],
    unit_of_work_factory: FakeUnitOfWorkFactory,
    correlation_id: str | None = SAMPLE_CORRELATION_ID,
) -> list[AuditEvent]:
    """Subscribes a fresh AuditSubscriber, publishes the events in one unit and returns rows."""
    event_bus = DomainEventBus()
    AuditSubscriber(SequentialIdGenerator(), lambda: correlation_id).subscribe_to(event_bus)
    with unit_of_work_factory() as unit_of_work:
        for event in events:
            event_bus.publish(event, unit_of_work)
    return unit_of_work_factory.database.audit_events


def test_audit_subscriber_writes_one_row_of_the_matching_type_per_event(
    unit_of_work_factory: FakeUnitOfWorkFactory,
) -> None:
    """All seven event types are audited, each as its own AuditEventType."""
    audit_events = _publish_through_audit(build_every_domain_event(), unit_of_work_factory)
    assert [audit_event.event_type for audit_event in audit_events] == list(AuditEventType)
    assert len(AUDIT_MAPPINGS_BY_EVENT_TYPE) == len(AuditEventType)


def test_audit_subscriber_maps_subject_moment_correlation_and_details(
    unit_of_work_factory: FakeUnitOfWorkFactory,
) -> None:
    """The subject is the attempt; details keep every other field, enums as stored words."""
    (audit_event,) = _publish_through_audit([build_payment_status_changed()], unit_of_work_factory)
    assert audit_event == AuditEvent(
        id="01JCTESTID0000000000000001",
        event_type=AuditEventType.PAYMENT_STATUS_CHANGED,
        subject_type="payment_attempt",
        subject_id=SAMPLE_ATTEMPT_ID,
        correlation_id=SAMPLE_CORRELATION_ID,
        occurred_at=CREATED_AT,
        details={
            "order_id": "ORDER-SAMPLE-0001",
            "previous_status": "LINK_CREATED",
            "new_status": "PAID",
            "reported_status": "PAID",
            "source": "WEBHOOK",
            "amount_in_paise": 2_200_000,
            "amount_paid_in_paise": 2_100_000,
            "gateway_transaction_id": "transaction-sample-0001",
        },
    )
    assert type(audit_event.details["new_status"]) is str


@pytest.mark.parametrize(
    ("event_index", "expected_subject_type", "expected_subject_id"),
    [
        (4, "webhook_delivery", "01JCSAMPLEDELIVERY00000001"),
        (5, "payment_order", "ORDER-UNKNOWN-0001"),
        (6, "emi_offer", "offer-plan-b"),
    ],
)
def test_audit_subscriber_uses_the_subject_that_identifies_each_non_attempt_event(
    unit_of_work_factory: FakeUnitOfWorkFactory,
    event_index: int,
    expected_subject_type: str,
    expected_subject_id: str,
) -> None:
    """Rejected webhooks, unknown orders and offers are audited under their own subjects."""
    event = build_every_domain_event()[event_index]
    (audit_event,) = _publish_through_audit([event], unit_of_work_factory)
    assert (audit_event.subject_type, audit_event.subject_id) == (
        expected_subject_type,
        expected_subject_id,
    )


def test_audit_subscriber_outside_a_request_records_no_correlation_id(
    unit_of_work_factory: FakeUnitOfWorkFactory,
) -> None:
    """Work done outside an HTTP request has no correlation id, and that is recorded as None."""
    (audit_event,) = _publish_through_audit(
        [build_payment_status_changed()], unit_of_work_factory, correlation_id=None
    )
    assert audit_event.correlation_id is None


def test_audit_subscriber_by_default_reads_the_request_correlation_id(
    unit_of_work_factory: FakeUnitOfWorkFactory,
) -> None:
    """Without an injected provider, the current request's correlation id is used."""
    context_token = correlation_id_context.set(SAMPLE_CORRELATION_ID)
    try:
        audit_subscriber = AuditSubscriber(SequentialIdGenerator())
        with unit_of_work_factory() as unit_of_work:
            audit_subscriber.record_event(build_payment_status_changed(), unit_of_work)
    finally:
        correlation_id_context.reset(context_token)
    assert unit_of_work_factory.database.audit_events[0].correlation_id == SAMPLE_CORRELATION_ID


def test_audit_subscriber_rejects_an_event_type_it_has_no_mapping_for(
    unit_of_work_factory: FakeUnitOfWorkFactory,
) -> None:
    """A new event type must be mapped on purpose; it is never audited by guesswork."""
    with unit_of_work_factory() as unit_of_work, pytest.raises(KeyError):
        AuditSubscriber(SequentialIdGenerator()).record_event(
            DomainEvent(occurred_at=CREATED_AT), unit_of_work
        )


def test_audit_subscriber_writes_nothing_when_the_unit_of_work_rolls_back(
    unit_of_work_factory: FakeUnitOfWorkFactory,
) -> None:
    """The audit row lives and dies with the publisher's transaction."""
    event_bus = DomainEventBus()
    AuditSubscriber(SequentialIdGenerator()).subscribe_to(event_bus)
    with pytest.raises(SimulatedUseCaseFailureError):
        _publish_then_fail(event_bus, unit_of_work_factory)
    assert unit_of_work_factory.database.audit_events == []
