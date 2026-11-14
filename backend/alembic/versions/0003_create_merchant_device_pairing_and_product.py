"""Create merchant, device_pairing and product for pairing auth and the counter catalogue.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-14

Every foreign key is indexed. Names are wrapped in op.f() because they already follow the
models naming convention.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> tuple[sa.Column[object], sa.Column[object]]:
    """Gives fresh created_at and updated_at columns, which every mutable table carries."""
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def _create_merchant_table() -> None:
    """Creates merchant with a unique shop code, the PIN hash and salt, and its lockout state."""
    op.create_table(
        "merchant",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("shop_code", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("counter_device_label", sa.String(64), nullable=False),
        sa.Column("pin_hash", sa.String(64), nullable=False),
        sa.Column("pin_salt", sa.String(32), nullable=False),
        sa.Column("failed_pin_attempt_count", sa.Integer(), nullable=False),
        sa.Column("pin_locked_until", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchant")),
        sa.UniqueConstraint("shop_code", name=op.f("uq_merchant_shop_code")),
        sa.CheckConstraint(
            "failed_pin_attempt_count >= 0",
            name=op.f("ck_merchant_failed_pin_attempt_count_not_negative"),
        ),
    )


def _create_device_pairing_table() -> None:
    """Creates device_pairing with a unique token hash and an indexed merchant foreign key."""
    op.create_table(
        "device_pairing",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("merchant_id", sa.String(26), nullable=False),
        sa.Column("device_label", sa.String(64), nullable=False),
        sa.Column("access_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_device_pairing")),
        sa.ForeignKeyConstraint(
            ["merchant_id"], ["merchant.id"], name=op.f("fk_device_pairing_merchant_id_merchant")
        ),
        sa.UniqueConstraint("access_token_hash", name=op.f("uq_device_pairing_access_token_hash")),
        sa.CheckConstraint(
            "char_length(access_token_hash) = 64",
            name=op.f("ck_device_pairing_access_token_hash_length"),
        ),
    )
    op.create_index(op.f("ix_device_pairing_merchant_id"), "device_pairing", ["merchant_id"])


def _create_product_table() -> None:
    """Creates product with a positive paise list price and an indexed merchant foreign key."""
    op.create_table(
        "product",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("merchant_id", sa.String(26), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("gateway_product_id", sa.String(128), nullable=False),
        sa.Column("gateway_brand_id", sa.String(128), nullable=False),
        sa.Column("gateway_category_id", sa.String(128), nullable=False),
        sa.Column("list_price_in_paise", sa.BigInteger(), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product")),
        sa.ForeignKeyConstraint(
            ["merchant_id"], ["merchant.id"], name=op.f("fk_product_merchant_id_merchant")
        ),
        sa.CheckConstraint(
            "list_price_in_paise > 0", name=op.f("ck_product_list_price_in_paise_positive")
        ),
    )
    op.create_index(op.f("ix_product_merchant_id"), "product", ["merchant_id"])


def upgrade() -> None:
    """Creates the three tables, merchant first because the other two refer to it."""
    _create_merchant_table()
    _create_device_pairing_table()
    _create_product_table()


def downgrade() -> None:
    """Drops the three tables and their indexes in reverse order, losing every pairing."""
    op.drop_index(op.f("ix_product_merchant_id"), table_name="product")
    op.drop_table("product")
    op.drop_index(op.f("ix_device_pairing_merchant_id"), table_name="device_pairing")
    op.drop_table("device_pairing")
    op.drop_table("merchant")
