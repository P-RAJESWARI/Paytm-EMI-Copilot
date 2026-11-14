"""ORM table for the append-only audit trail; a database trigger rejects UPDATE and DELETE."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.domain.payments import AuditDetailValue, AuditEventType
from emi_copilot.models.base import Base, sql_value_list


class AuditEventModel(Base):
    """One row per audit event; append-only, so there is no updated_at column.

    created_at is when the row was written; occurred_at is when the recorded event happened.
    """

    __tablename__ = "audit_event"
    __table_args__ = (
        CheckConstraint(
            f"event_type IN ({sql_value_list(AuditEventType)})", name="event_type_known"
        ),
        Index(None, "subject_type", "subject_id"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    subject_type: Mapped[str] = mapped_column(String(64))
    subject_id: Mapped[str] = mapped_column(String(64))
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    details: Mapped[dict[str, AuditDetailValue]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
