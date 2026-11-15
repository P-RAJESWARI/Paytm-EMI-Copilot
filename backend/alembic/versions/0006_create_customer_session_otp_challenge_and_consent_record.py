"""Create customer_session, consent_otp_challenge and the append-only consent_record.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-15

Enum values are copied here, not imported, so this revision stays fixed when the code changes.
Every foreign key is indexed: customer_session.sale_id by its own index, the challenge's
customer_session_id by (customer_session_id, created_at), consent_record.sale_id by its unique
constraint (one consent per sale) and consent_record.customer_session_id by its own index.
consent_record reuses 0004's reject_append_only_table_modification() guard function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COMFORT_CHECK_STATUSES = ("NOT_ASKED", "COMPLETED", "SKIPPED")
_CUSTOMER_LANGUAGES = ("en", "ta")
_GENESIS_PREVIOUS_RECORD_HASH = "0" * 64
_LAYER_2_AUDIT_EVENT_TYPES = (
    "PAYMENT_LINK_CREATED",
    "PAYMENT_LINK_CREATION_FAILED",
    "PAYMENT_LINK_OUTCOME_UNKNOWN",
    "PAYMENT_STATUS_CHANGED",
    "WEBHOOK_REJECTED",
    "WEBHOOK_PROCESSED",
    "OFFER_QUOTE_MISMATCH",
    "SALE_STARTED",
    "SALE_STATUS_CHANGED",
    "SALE_PAYMENT_OUTCOME_IGNORED",
)
_CUSTOMER_FLOW_AUDIT_EVENT_TYPES = (
    "CUSTOMER_SESSION_STARTED",
    "OTP_VERIFICATION_FAILED",
    "CONSENT_RECORDED",
)
_AUDIT_EVENT_TYPE_CHECK_NAME = "ck_audit_event_event_type_known"

_CREATE_CONSENT_ROW_GUARD_TRIGGER = """
CREATE TRIGGER consent_record_reject_update_or_delete
BEFORE UPDATE OR DELETE ON consent_record
FOR EACH ROW EXECUTE FUNCTION reject_append_only_table_modification()
"""
_CREATE_CONSENT_TRUNCATE_GUARD_TRIGGER = """
CREATE TRIGGER consent_record_reject_truncate
BEFORE TRUNCATE ON consent_record
FOR EACH STATEMENT EXECUTE FUNCTION reject_append_only_table_modification()
"""


def _sql_value_list(values: Sequence[str]) -> str:
    """Renders fixed values as a SQL IN list for a CHECK constraint."""
    return ", ".join(f"'{value}'" for value in values)


def _create_customer_session_table() -> None:
    """Creates customer_session: the token only as a unique hash, the budget in BIGINT paise."""
    op.create_table(
        "customer_session",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("sale_id", sa.String(26), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("monthly_budget_in_paise", sa.BigInteger(), nullable=True),
        sa.Column("comfort_check_status", sa.String(16), nullable=False),
        sa.Column("language", sa.String(2), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_session")),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sale.id"], name=op.f("fk_customer_session_sale_id_sale")
        ),
        sa.UniqueConstraint("token_hash", name=op.f("uq_customer_session_token_hash")),
        sa.CheckConstraint(
            "char_length(token_hash) = 64", name=op.f("ck_customer_session_token_hash_length")
        ),
        sa.CheckConstraint(
            "monthly_budget_in_paise > 0",
            name=op.f("ck_customer_session_monthly_budget_in_paise_positive"),
        ),
        sa.CheckConstraint(
            f"comfort_check_status IN ({_sql_value_list(_COMFORT_CHECK_STATUSES)})",
            name=op.f("ck_customer_session_comfort_check_status_known"),
        ),
        sa.CheckConstraint(
            f"language IN ({_sql_value_list(_CUSTOMER_LANGUAGES)})",
            name=op.f("ck_customer_session_language_known"),
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name=op.f("ck_customer_session_expires_after_start")
        ),
    )
    op.create_index(op.f("ix_customer_session_sale_id"), "customer_session", ["sale_id"])


def _create_consent_otp_challenge_table() -> None:
    """Creates consent_otp_challenge: the code only as a keyed hash, with its attempts left."""
    op.create_table(
        "consent_otp_challenge",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("customer_session_id", sa.String(26), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("attempts_remaining", sa.SmallInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consent_otp_challenge")),
        sa.ForeignKeyConstraint(
            ["customer_session_id"],
            ["customer_session.id"],
            name=op.f("fk_consent_otp_challenge_customer_session_id_customer_session"),
        ),
        sa.CheckConstraint(
            "char_length(code_hash) = 64", name=op.f("ck_consent_otp_challenge_code_hash_length")
        ),
        sa.CheckConstraint(
            "attempts_remaining >= 0",
            name=op.f("ck_consent_otp_challenge_attempts_remaining_not_negative"),
        ),
    )
    op.create_index(
        op.f("ix_consent_otp_challenge_customer_session_id_created_at"),
        "consent_otp_challenge",
        ["customer_session_id", "created_at"],
    )


def _consent_record_columns() -> tuple[sa.Column[object], ...]:
    """Gives the consent_record columns: evidence, chain links and the replay key; no updated_at."""
    return (
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("chain_position", sa.BigInteger(), nullable=False),
        sa.Column("sale_id", sa.String(26), nullable=False),
        sa.Column("customer_session_id", sa.String(26), nullable=False),
        sa.Column("consent_reference", sa.String(13), nullable=False),
        sa.Column("plan_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("phone_last_two_digits", sa.String(2), nullable=False),
        sa.Column("phone_hash", sa.String(64), nullable=False),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("cooling_off_wording_version", sa.String(64), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_record_hash", sa.String(64), nullable=False),
        sa.Column("record_hash", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _consent_record_constraints() -> tuple[sa.Constraint, ...]:
    """Gives the keys and checks: one consent per sale and a chain that can never fork."""
    return (
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consent_record")),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sale.id"], name=op.f("fk_consent_record_sale_id_sale")
        ),
        sa.ForeignKeyConstraint(
            ["customer_session_id"],
            ["customer_session.id"],
            name=op.f("fk_consent_record_customer_session_id_customer_session"),
        ),
        sa.UniqueConstraint("sale_id", name=op.f("uq_consent_record_sale_id")),
        sa.UniqueConstraint("chain_position", name=op.f("uq_consent_record_chain_position")),
        sa.UniqueConstraint(
            "previous_record_hash", name=op.f("uq_consent_record_previous_record_hash")
        ),
        sa.UniqueConstraint("record_hash", name=op.f("uq_consent_record_record_hash")),
        sa.CheckConstraint(
            "chain_position >= 1", name=op.f("ck_consent_record_chain_position_positive")
        ),
        sa.CheckConstraint(
            f"(chain_position = 1) = (previous_record_hash = '{_GENESIS_PREVIOUS_RECORD_HASH}')",
            name=op.f("ck_consent_record_genesis_link_only_first"),
        ),
        sa.CheckConstraint(
            "phone_last_two_digits ~ '^[0-9]{2}$'",
            name=op.f("ck_consent_record_phone_last_two_digits_only"),
        ),
        sa.CheckConstraint(
            f"language IN ({_sql_value_list(_CUSTOMER_LANGUAGES)})",
            name=op.f("ck_consent_record_language_known"),
        ),
    )


def _create_consent_record_table() -> None:
    """Creates consent_record, indexes its session link and guards it as append-only."""
    op.create_table("consent_record", *_consent_record_columns(), *_consent_record_constraints())
    op.create_index(
        op.f("ix_consent_record_customer_session_id"), "consent_record", ["customer_session_id"]
    )
    op.execute(_CREATE_CONSENT_ROW_GUARD_TRIGGER)
    op.execute(_CREATE_CONSENT_TRUNCATE_GUARD_TRIGGER)


def _replace_audit_event_type_check(event_types: Sequence[str], *, is_validated: bool) -> None:
    """Swaps the audit_event type check; NOT VALID keeps rows of types the new list drops."""
    op.execute(f"ALTER TABLE audit_event DROP CONSTRAINT {_AUDIT_EVENT_TYPE_CHECK_NAME}")
    op.execute(
        f"ALTER TABLE audit_event ADD CONSTRAINT {_AUDIT_EVENT_TYPE_CHECK_NAME} "
        f"CHECK (event_type IN ({_sql_value_list(event_types)}))"
        + ("" if is_validated else " NOT VALID")
    )


def upgrade() -> None:
    """Creates the three customer flow tables and allows their audit event types."""
    _create_customer_session_table()
    _create_consent_otp_challenge_table()
    _create_consent_record_table()
    _replace_audit_event_type_check(
        (*_LAYER_2_AUDIT_EVENT_TYPES, *_CUSTOMER_FLOW_AUDIT_EVENT_TYPES), is_validated=True
    )


def downgrade() -> None:
    """Reverses upgrade. The append-only guard is dropped first, so consent rows are lost too.

    The restored audit type check is NOT VALID, because audit_event rows can never be deleted,
    so customer flow audit rows written meanwhile would otherwise block the downgrade.
    """
    _replace_audit_event_type_check(_LAYER_2_AUDIT_EVENT_TYPES, is_validated=False)
    op.execute("DROP TRIGGER consent_record_reject_truncate ON consent_record")
    op.execute("DROP TRIGGER consent_record_reject_update_or_delete ON consent_record")
    op.drop_index(op.f("ix_consent_record_customer_session_id"), table_name="consent_record")
    op.drop_table("consent_record")
    op.drop_index(
        op.f("ix_consent_otp_challenge_customer_session_id_created_at"),
        table_name="consent_otp_challenge",
    )
    op.drop_table("consent_otp_challenge")
    op.drop_index(op.f("ix_customer_session_sale_id"), table_name="customer_session")
    op.drop_table("customer_session")
