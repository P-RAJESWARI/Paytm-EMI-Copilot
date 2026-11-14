"""Integration tests for the append-only AuditEventRepository and the database trigger behind it."""

from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.payments import AuditEventType
from emi_copilot.repositories.audit_event_repository import AuditEventRepository
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT, build_audit_event

pytestmark = pytest.mark.integration


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Opens one session for the test; its changes vanish with the outer transaction."""
    with session_factory() as session:
        yield session


@pytest.fixture
def repository(session: Session, fixed_clock: FixedClock) -> AuditEventRepository:
    """Builds the repository on the test session and the fixed clock."""
    return AuditEventRepository(session, fixed_clock)


def test_audit_event_repository_public_api_is_append_and_reads_only() -> None:
    """No update, delete or other write path exists on the audit trail (security section 9)."""
    public_names = {name for name in dir(AuditEventRepository) if not name.startswith("_")}
    assert public_names == {"append", "list_by_event_type", "list_for_subject"}


def test_append_then_list_for_subject_returns_equal_events_oldest_first(
    repository: AuditEventRepository, session: Session
) -> None:
    """Events about one subject come back unchanged, ordered by when they happened."""
    later_event = build_audit_event(1, occurred_at=CREATED_AT + timedelta(seconds=5))
    earlier_event = build_audit_event(
        2,
        event_type=AuditEventType.PAYMENT_STATUS_CHANGED,
        correlation_id=None,
        details={"status": "PAID", "amount_in_paise": 2_200_000, "is_replay": False, "note": None},
    )
    other_subject_event = build_audit_event(3, subject_id="01JCSAMPLEATTEMPT000000099")
    for audit_event in (later_event, earlier_event, other_subject_event):
        repository.append(audit_event)
    session.expunge_all()
    assert repository.list_for_subject("payment_attempt", later_event.subject_id) == (
        earlier_event,
        later_event,
    )


def test_list_by_event_type_returns_only_that_type(repository: AuditEventRepository) -> None:
    """Listing by type filters on the indexed event_type column."""
    rejected_event = build_audit_event(1, event_type=AuditEventType.WEBHOOK_REJECTED)
    repository.append(rejected_event)
    repository.append(build_audit_event(2))
    assert repository.list_by_event_type(AuditEventType.WEBHOOK_REJECTED) == (rejected_event,)
    assert repository.list_by_event_type(AuditEventType.OFFER_QUOTE_MISMATCH) == ()


def test_append_stamps_created_at_from_the_injected_clock(
    repository: AuditEventRepository, session: Session, fixed_clock: FixedClock
) -> None:
    """created_at records when the row was written, from the clock, separately from occurred_at."""
    fixed_clock.advance(timedelta(minutes=1))
    audit_event = build_audit_event()
    repository.append(audit_event)
    stored_row = session.execute(
        text("SELECT occurred_at, created_at FROM audit_event WHERE id = :id"),
        {"id": audit_event.id},
    ).one()
    assert stored_row.occurred_at == CREATED_AT
    assert stored_row.created_at == CREATED_AT + timedelta(minutes=1)


@pytest.mark.parametrize(
    "modifying_statement",
    [
        "UPDATE audit_event SET subject_id = 'tampered' WHERE id = :id",
        "DELETE FROM audit_event WHERE id = :id",
        "TRUNCATE audit_event",
    ],
)
def test_raw_sql_modifying_audit_event_is_rejected_by_trigger(
    repository: AuditEventRepository, database_connection: Connection, modifying_statement: str
) -> None:
    """Even SQL that bypasses the repository cannot change or remove audit evidence."""
    audit_event = build_audit_event()
    repository.append(audit_event)
    with (
        pytest.raises(ProgrammingError, match="audit_event is append-only"),
        database_connection.begin_nested(),
    ):
        database_connection.execute(text(modifying_statement), {"id": audit_event.id})
    assert repository.list_for_subject("payment_attempt", audit_event.subject_id) == (audit_event,)
