"""Create weekly_message and index funnel_event by merchant, stage and moment.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-14

weekly_message.merchant_id is indexed by its (merchant_id, period_start_date) unique constraint.
The report's cohort queries start from sale (merchant_id, started_at), already indexed in 0004,
and join funnel_event on its (sale_id, stage) unique constraint.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Creates weekly_message and the funnel_event stage index."""
    op.create_table(
        "weekly_message",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("merchant_id", sa.String(26), nullable=False),
        sa.Column("period_start_date", sa.Date(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "EXTRACT(ISODOW FROM period_start_date) = 1",
            name=op.f("ck_weekly_message_period_start_date_is_monday"),
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchant.id"],
            name=op.f("fk_weekly_message_merchant_id_merchant"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weekly_message")),
        sa.UniqueConstraint(
            "merchant_id",
            "period_start_date",
            name=op.f("uq_weekly_message_merchant_id_period_start_date"),
        ),
    )
    op.create_index(
        op.f("ix_funnel_event_merchant_id_stage_occurred_at"),
        "funnel_event",
        ["merchant_id", "stage", "occurred_at"],
    )


def downgrade() -> None:
    """Drops the index and weekly_message, losing which weekly messages were sent."""
    op.drop_index(op.f("ix_funnel_event_merchant_id_stage_occurred_at"), table_name="funnel_event")
    op.drop_table("weekly_message")
