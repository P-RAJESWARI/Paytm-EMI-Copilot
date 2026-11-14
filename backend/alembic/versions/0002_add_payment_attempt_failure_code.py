"""Add payment_attempt.failure_code, why a create-link call certainly made no link.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14

Nullable: only LINK_CREATION_FAILED attempts carry a code. The values are copied here, not
imported, so this revision stays fixed when the code changes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PAYMENT_LINK_FAILURE_CODES = (
    "GATEWAY_UNAVAILABLE",
    "INVALID_REQUEST",
    "DUPLICATE_ORDER_ID",
    "OPERATION_NOT_PERMITTED",
    "GATEWAY_INTERNAL_ERROR",
)
_FAILURE_CODE_CHECK_NAME = "ck_payment_attempt_failure_code_known"


def upgrade() -> None:
    """Adds the nullable failure_code column and the check that it holds a known code."""
    op.add_column("payment_attempt", sa.Column("failure_code", sa.String(32), nullable=True))
    known_codes = ", ".join(f"'{failure_code}'" for failure_code in _PAYMENT_LINK_FAILURE_CODES)
    op.create_check_constraint(
        op.f(_FAILURE_CODE_CHECK_NAME), "payment_attempt", f"failure_code IN ({known_codes})"
    )


def downgrade() -> None:
    """Drops the check and then the column, which loses every stored failure code."""
    op.drop_constraint(op.f(_FAILURE_CODE_CHECK_NAME), "payment_attempt", type_="check")
    op.drop_column("payment_attempt", "failure_code")
