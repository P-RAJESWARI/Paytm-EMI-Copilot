"""Integration tests: the audit subscriber's rows round-trip through PostgreSQL unchanged."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.payments import AuditEvent, AuditEventType
from emi_copilot.events.audit_subscriber import AuditSubscriber
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.event_builders import build_every_domain_event
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock

pytestmark = pytest.mark.integration


def _read_every_audit_event(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> list[AuditEvent]:
    """Reads every stored audit event, grouped by type in AuditEventType order."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        return [
            audit_event
            for event_type in AuditEventType
            for audit_event in unit_of_work.audit_events.list_by_event_type(event_type)
        ]


def test_audit_subscriber_rows_for_every_event_type_are_stored_as_written(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Each event's details, enums as plain words and paise as integers, survive JSONB storage."""
    event_bus = DomainEventBus()
    AuditSubscriber(SequentialIdGenerator(), lambda: "correlation-sample-0001").subscribe_to(
        event_bus
    )
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        for event in build_every_domain_event():
            event_bus.publish(event, unit_of_work)
    stored_audit_events = _read_every_audit_event(session_factory, fixed_clock)
    assert [audit_event.event_type for audit_event in stored_audit_events] == list(AuditEventType)
    status_changed_details = dict(stored_audit_events[3].details)
    assert status_changed_details["new_status"] == "PAID"
    assert status_changed_details["amount_paid_in_paise"] == 2_100_000
    assert stored_audit_events[3].correlation_id == "correlation-sample-0001"
