"""Appends and reads audit events; this repository deliberately has no update or delete method."""

from collections.abc import Sequence
from datetime import UTC

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.payments import AuditEvent, AuditEventType
from emi_copilot.models import AuditEventModel


def _to_domain(audit_event_model: AuditEventModel) -> AuditEvent:
    """Maps an ORM row back to a validated domain event; occurred_at is returned in UTC."""
    return AuditEvent(
        id=audit_event_model.id,
        event_type=AuditEventType(audit_event_model.event_type),
        subject_type=audit_event_model.subject_type,
        subject_id=audit_event_model.subject_id,
        correlation_id=audit_event_model.correlation_id,
        occurred_at=audit_event_model.occurred_at.astimezone(UTC),
        details=audit_event_model.details,
    )


# Pattern: Repository. The append-only audit trail; the missing update/delete is the point.
class AuditEventRepository:
    """Appends audit events and reads them back, oldest first, inside the unit of work's session.

    A database trigger also rejects UPDATE, DELETE and TRUNCATE on audit_event, so evidence
    stays intact even if code outside this class tries (security-and-compliance.md section 9).
    """

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for each row's created_at."""
        self._session = session
        self._clock = clock

    def append(self, audit_event: AuditEvent) -> None:
        """Inserts one audit event, stamped with the moment it was written, and flushes it now."""
        self._session.add(
            AuditEventModel(
                id=audit_event.id,
                event_type=audit_event.event_type.value,
                subject_type=audit_event.subject_type,
                subject_id=audit_event.subject_id,
                correlation_id=audit_event.correlation_id,
                occurred_at=audit_event.occurred_at,
                details=dict(audit_event.details),
                created_at=self._clock.now(),
            )
        )
        self._session.flush()

    def list_for_subject(self, subject_type: str, subject_id: str) -> Sequence[AuditEvent]:
        """Returns every event about one subject, such as one payment attempt, oldest first."""
        return self._list_where(
            (AuditEventModel.subject_type == subject_type)
            & (AuditEventModel.subject_id == subject_id)
        )

    def list_by_event_type(self, event_type: AuditEventType) -> Sequence[AuditEvent]:
        """Returns every event of one type, oldest first."""
        return self._list_where(AuditEventModel.event_type == event_type.value)

    def _list_where(self, condition: ColumnElement[bool]) -> Sequence[AuditEvent]:
        """Loads matching events ordered by when they happened, then by id for a stable order."""
        audit_event_models = self._session.scalars(
            select(AuditEventModel)
            .where(condition)
            .order_by(AuditEventModel.occurred_at, AuditEventModel.id)
        ).all()
        return tuple(_to_domain(audit_event_model) for audit_event_model in audit_event_models)
