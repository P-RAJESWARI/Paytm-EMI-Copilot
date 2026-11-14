"""Create sale and the append-only funnel_event, link payment_attempt.sale_id, add audit types.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-14

Enum values are copied here, not imported, so this revision stays fixed when the code changes.
Every foreign key is indexed: sale.merchant_id leads two composite indexes, funnel_event.sale_id
leads its unique constraint and funnel_event.merchant_id leads its report index.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SALE_STATUSES = ("CHOOSING", "READY_TO_PAY", "PAID", "PAYMENT_NOT_COMPLETED", "EXPIRED")
_STATUSES_WITH_CHOSEN_PLAN = ("PAID", "PAYMENT_NOT_COMPLETED", "READY_TO_PAY")
_OPEN_SALE_STATUSES = ("CHOOSING", "PAYMENT_NOT_COMPLETED", "READY_TO_PAY")
_FUNNEL_STAGES = ("STARTED", "BUDGET_TOLD", "PLANS_VIEWED", "AGREED", "PAID")
_LAYER_1_AUDIT_EVENT_TYPES = (
    "PAYMENT_LINK_CREATED",
    "PAYMENT_LINK_CREATION_FAILED",
    "PAYMENT_LINK_OUTCOME_UNKNOWN",
    "PAYMENT_STATUS_CHANGED",
    "WEBHOOK_REJECTED",
    "WEBHOOK_PROCESSED",
    "OFFER_QUOTE_MISMATCH",
)
_SALE_AUDIT_EVENT_TYPES = ("SALE_STARTED", "SALE_STATUS_CHANGED", "SALE_PAYMENT_OUTCOME_IGNORED")
_AUDIT_EVENT_TYPE_CHECK_NAME = "ck_audit_event_event_type_known"

# Same defence in depth as audit_event (0001), with one function any append-only table can use.
_CREATE_APPEND_ONLY_GUARD_FUNCTION = """
CREATE FUNCTION reject_append_only_table_modification() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% is append-only: % is not allowed', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$
"""
_CREATE_FUNNEL_ROW_GUARD_TRIGGER = """
CREATE TRIGGER funnel_event_reject_update_or_delete
BEFORE UPDATE OR DELETE ON funnel_event
FOR EACH ROW EXECUTE FUNCTION reject_append_only_table_modification()
"""
_CREATE_FUNNEL_TRUNCATE_GUARD_TRIGGER = """
CREATE TRIGGER funnel_event_reject_truncate
BEFORE TRUNCATE ON funnel_event
FOR EACH STATEMENT EXECUTE FUNCTION reject_append_only_table_modification()
"""


def _sql_value_list(values: Sequence[str]) -> str:
    """Renders fixed enum values as a SQL IN list for a CHECK constraint or index predicate."""
    return ", ".join(f"'{value}'" for value in values)


def _timestamp_columns() -> tuple[sa.Column[object], sa.Column[object]]:
    """Gives fresh created_at and updated_at columns, which every mutable table carries."""
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def _sale_columns() -> tuple[sa.Column[object], ...]:
    """Gives the sale columns: price in BIGINT paise, the QR nonce hash, the frozen plan."""
    return (
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("merchant_id", sa.String(26), nullable=False),
        sa.Column("product_id", sa.String(26), nullable=False),
        sa.Column("price_in_paise", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("session_code", sa.String(4), nullable=False),
        sa.Column("qr_token_nonce_hash", sa.String(64), nullable=False),
        sa.Column("qr_token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("qr_token_exchanged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chosen_plan_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("request_fingerprint", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamp_columns(),
    )


def _sale_constraints() -> tuple[sa.Constraint, ...]:
    """Gives the sale keys and checks: known status, four-digit code, plan exactly once agreed."""
    return (
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale")),
        sa.ForeignKeyConstraint(
            ["merchant_id"], ["merchant.id"], name=op.f("fk_sale_merchant_id_merchant")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["product.id"], name=op.f("fk_sale_product_id_product")
        ),
        sa.UniqueConstraint(
            "merchant_id", "idempotency_key", name=op.f("uq_sale_merchant_id_idempotency_key")
        ),
        sa.CheckConstraint("price_in_paise > 0", name=op.f("ck_sale_price_in_paise_positive")),
        sa.CheckConstraint(
            f"status IN ({_sql_value_list(_SALE_STATUSES)})", name=op.f("ck_sale_status_known")
        ),
        sa.CheckConstraint(
            "session_code ~ '^[0-9]{4}$'", name=op.f("ck_sale_session_code_four_digits")
        ),
        sa.CheckConstraint(
            "char_length(qr_token_nonce_hash) = 64",
            name=op.f("ck_sale_qr_token_nonce_hash_length"),
        ),
        sa.CheckConstraint(
            "(chosen_plan_snapshot IS NOT NULL) = "
            f"(status IN ({_sql_value_list(_STATUSES_WITH_CHOSEN_PLAN)}))",
            name=op.f("ck_sale_chosen_plan_iff_agreed"),
        ),
        sa.CheckConstraint(
            "(idempotency_key IS NULL) = (request_fingerprint IS NULL)",
            name=op.f("ck_sale_idempotency_key_with_fingerprint"),
        ),
    )


def _create_sale_table() -> None:
    """Creates sale with its merchant indexes and the open-sale session code uniqueness."""
    op.create_table("sale", *_sale_columns(), *_sale_constraints())
    op.create_index(op.f("ix_sale_product_id"), "sale", ["product_id"])
    op.create_index(op.f("ix_sale_merchant_id_status"), "sale", ["merchant_id", "status"])
    op.create_index(op.f("ix_sale_merchant_id_started_at"), "sale", ["merchant_id", "started_at"])
    op.create_index(
        op.f("uq_sale_merchant_id_session_code_open"),
        "sale",
        ["merchant_id", "session_code"],
        unique=True,
        postgresql_where=sa.text(f"status IN ({_sql_value_list(_OPEN_SALE_STATUSES)})"),
    )


def _create_funnel_event_table() -> None:
    """Creates funnel_event (no updated_at): one row per sale and stage, budget only if told."""
    op.create_table(
        "funnel_event",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("sale_id", sa.String(26), nullable=False),
        sa.Column("merchant_id", sa.String(26), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("monthly_budget_in_paise", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_funnel_event")),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sale.id"], name=op.f("fk_funnel_event_sale_id_sale")
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"], ["merchant.id"], name=op.f("fk_funnel_event_merchant_id_merchant")
        ),
        sa.UniqueConstraint("sale_id", "stage", name=op.f("uq_funnel_event_sale_id_stage")),
        sa.CheckConstraint(
            f"stage IN ({_sql_value_list(_FUNNEL_STAGES)})",
            name=op.f("ck_funnel_event_stage_known"),
        ),
        sa.CheckConstraint(
            "(monthly_budget_in_paise IS NOT NULL) = (stage = 'BUDGET_TOLD')",
            name=op.f("ck_funnel_event_monthly_budget_only_on_budget_told"),
        ),
        sa.CheckConstraint(
            "monthly_budget_in_paise > 0",
            name=op.f("ck_funnel_event_monthly_budget_in_paise_positive"),
        ),
    )
    op.create_index(
        op.f("ix_funnel_event_merchant_id_occurred_at"),
        "funnel_event",
        ["merchant_id", "occurred_at"],
    )
    op.execute(_CREATE_APPEND_ONLY_GUARD_FUNCTION)
    op.execute(_CREATE_FUNNEL_ROW_GUARD_TRIGGER)
    op.execute(_CREATE_FUNNEL_TRUNCATE_GUARD_TRIGGER)


def _replace_audit_event_type_check(event_types: Sequence[str], *, is_validated: bool) -> None:
    """Swaps the audit_event type check; NOT VALID keeps rows of types the new list drops."""
    op.execute(f"ALTER TABLE audit_event DROP CONSTRAINT {_AUDIT_EVENT_TYPE_CHECK_NAME}")
    op.execute(
        f"ALTER TABLE audit_event ADD CONSTRAINT {_AUDIT_EVENT_TYPE_CHECK_NAME} "
        f"CHECK (event_type IN ({_sql_value_list(event_types)}))"
        + ("" if is_validated else " NOT VALID")
    )


def upgrade() -> None:
    """Creates sale and funnel_event, links payment attempts to sales and allows sale audits."""
    _create_sale_table()
    _create_funnel_event_table()
    op.add_column("payment_attempt", sa.Column("sale_id", sa.String(26), nullable=True))
    op.create_foreign_key(
        op.f("fk_payment_attempt_sale_id_sale"), "payment_attempt", "sale", ["sale_id"], ["id"]
    )
    op.create_index(op.f("ix_payment_attempt_sale_id"), "payment_attempt", ["sale_id"])
    _replace_audit_event_type_check(
        (*_LAYER_1_AUDIT_EVENT_TYPES, *_SALE_AUDIT_EVENT_TYPES), is_validated=True
    )


def downgrade() -> None:
    """Reverses upgrade, losing every sale and funnel row; sale audit rows stay (append-only).

    The restored audit type check is NOT VALID, because audit_event rows can never be deleted,
    so sale audit rows written meanwhile would otherwise block the downgrade.
    """
    _replace_audit_event_type_check(_LAYER_1_AUDIT_EVENT_TYPES, is_validated=False)
    op.drop_index(op.f("ix_payment_attempt_sale_id"), table_name="payment_attempt")
    op.drop_constraint(
        op.f("fk_payment_attempt_sale_id_sale"), "payment_attempt", type_="foreignkey"
    )
    op.drop_column("payment_attempt", "sale_id")
    op.execute("DROP TRIGGER funnel_event_reject_truncate ON funnel_event")
    op.execute("DROP TRIGGER funnel_event_reject_update_or_delete ON funnel_event")
    op.execute("DROP FUNCTION reject_append_only_table_modification()")
    op.drop_index(op.f("ix_funnel_event_merchant_id_occurred_at"), table_name="funnel_event")
    op.drop_table("funnel_event")
    op.drop_index(op.f("uq_sale_merchant_id_session_code_open"), table_name="sale")
    op.drop_index(op.f("ix_sale_merchant_id_started_at"), table_name="sale")
    op.drop_index(op.f("ix_sale_merchant_id_status"), table_name="sale")
    op.drop_index(op.f("ix_sale_product_id"), table_name="sale")
    op.drop_table("sale")
