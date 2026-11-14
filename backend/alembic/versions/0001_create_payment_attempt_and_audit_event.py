"""Create payment_attempt and the append-only audit_event table with its guard trigger.

Revision ID: 0001
Revises:
Create Date: 2026-11-14

Enum values are copied here, not imported, so this revision stays fixed when the code changes.
Names are wrapped in op.f() because they already follow the models naming convention.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PAYMENT_ATTEMPT_STATUSES = (
    "LINK_CREATION_IN_PROGRESS",
    "LINK_CREATED",
    "LINK_CREATION_FAILED",
    "OUTCOME_UNKNOWN",
    "PAYMENT_PENDING",
    "PAID",
    "PAYMENT_FAILED",
)
_AUDIT_EVENT_TYPES = (
    "PAYMENT_LINK_CREATED",
    "PAYMENT_LINK_CREATION_FAILED",
    "PAYMENT_LINK_OUTCOME_UNKNOWN",
    "PAYMENT_STATUS_CHANGED",
    "WEBHOOK_REJECTED",
    "WEBHOOK_PROCESSED",
    "OFFER_QUOTE_MISMATCH",
)

# Defence in depth (security-and-compliance.md section 9): even code that bypasses the
# repository, or a person with a SQL prompt, cannot change or remove audit evidence.
_CREATE_APPEND_ONLY_GUARD_FUNCTION = """
CREATE FUNCTION reject_audit_event_modification() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_event is append-only: % is not allowed', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$
"""
_CREATE_ROW_GUARD_TRIGGER = """
CREATE TRIGGER audit_event_reject_update_or_delete
BEFORE UPDATE OR DELETE ON audit_event
FOR EACH ROW EXECUTE FUNCTION reject_audit_event_modification()
"""
_CREATE_TRUNCATE_GUARD_TRIGGER = """
CREATE TRIGGER audit_event_reject_truncate
BEFORE TRUNCATE ON audit_event
FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_event_modification()
"""


def _sql_value_list(values: Sequence[str]) -> str:
    """Renders fixed enum values as a SQL IN list for a CHECK constraint."""
    return ", ".join(f"'{value}'" for value in values)


def _create_payment_attempt_table() -> None:
    """Creates payment_attempt with unique order and idempotency keys and positive paise."""
    op.create_table(
        "payment_attempt",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("amount_in_paise", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("offer_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("gateway_mode", sa.String(16), nullable=False),
        sa.Column("gateway_link_id", sa.String(128), nullable=True),
        sa.Column("payment_link_url", sa.String(2048), nullable=True),
        sa.Column("gateway_transaction_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_attempt")),
        sa.UniqueConstraint("order_id", name=op.f("uq_payment_attempt_order_id")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_payment_attempt_idempotency_key")),
        sa.CheckConstraint(
            "amount_in_paise > 0", name=op.f("ck_payment_attempt_amount_in_paise_positive")
        ),
        sa.CheckConstraint(
            f"status IN ({_sql_value_list(_PAYMENT_ATTEMPT_STATUSES)})",
            name=op.f("ck_payment_attempt_status_known"),
        ),
        sa.CheckConstraint(
            "char_length(request_fingerprint) = 64",
            name=op.f("ck_payment_attempt_request_fingerprint_length"),
        ),
    )


def _create_audit_event_table() -> None:
    """Creates audit_event (no updated_at) with indexes for type, subject and time lookups."""
    op.create_table(
        "audit_event",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("subject_type", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_event")),
        sa.CheckConstraint(
            f"event_type IN ({_sql_value_list(_AUDIT_EVENT_TYPES)})",
            name=op.f("ck_audit_event_event_type_known"),
        ),
    )
    op.create_index(op.f("ix_audit_event_event_type"), "audit_event", ["event_type"])
    op.create_index(
        op.f("ix_audit_event_subject_type_subject_id"),
        "audit_event",
        ["subject_type", "subject_id"],
    )
    op.create_index(op.f("ix_audit_event_occurred_at"), "audit_event", ["occurred_at"])


def upgrade() -> None:
    """Creates both tables and the trigger that keeps audit_event append-only."""
    _create_payment_attempt_table()
    _create_audit_event_table()
    op.execute(_CREATE_APPEND_ONLY_GUARD_FUNCTION)
    op.execute(_CREATE_ROW_GUARD_TRIGGER)
    op.execute(_CREATE_TRUNCATE_GUARD_TRIGGER)


def downgrade() -> None:
    """Drops the guard triggers, the guard function and both tables, in reverse order."""
    op.execute("DROP TRIGGER audit_event_reject_truncate ON audit_event")
    op.execute("DROP TRIGGER audit_event_reject_update_or_delete ON audit_event")
    op.execute("DROP FUNCTION reject_audit_event_modification()")
    op.drop_index(op.f("ix_audit_event_occurred_at"), table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_subject_type_subject_id"), table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_event_type"), table_name="audit_event")
    op.drop_table("audit_event")
    op.drop_table("payment_attempt")
