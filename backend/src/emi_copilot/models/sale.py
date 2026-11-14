"""ORM table for counter sales: price in integer paise, the QR token only as its nonce hash."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.domain.sales import OPEN_SALE_STATUSES, STATUSES_WITH_CHOSEN_PLAN, SaleStatus
from emi_copilot.models.base import Base, sql_member_list, sql_value_list

OPEN_SESSION_CODE_INDEX_NAME = "uq_sale_merchant_id_session_code_open"


class SaleModel(Base):
    """One row per sale; every merchant query filters on merchant_id first.

    The chosen plan is stored exactly once the customer has agreed to one, and a session code is
    unique among one shop's open sales (a partial unique index).
    """

    __tablename__ = "sale"
    __table_args__ = (
        CheckConstraint("price_in_paise > 0", name="price_in_paise_positive"),
        CheckConstraint(f"status IN ({sql_value_list(SaleStatus)})", name="status_known"),
        CheckConstraint("session_code ~ '^[0-9]{4}$'", name="session_code_four_digits"),
        CheckConstraint("char_length(qr_token_nonce_hash) = 64", name="qr_token_nonce_hash_length"),
        CheckConstraint(
            "(chosen_plan_snapshot IS NOT NULL) = "
            f"(status IN ({sql_member_list(STATUSES_WITH_CHOSEN_PLAN)}))",
            name="chosen_plan_iff_agreed",
        ),
        CheckConstraint(
            "(idempotency_key IS NULL) = (request_fingerprint IS NULL)",
            name="idempotency_key_with_fingerprint",
        ),
        UniqueConstraint("merchant_id", "idempotency_key"),
        Index(None, "merchant_id", "status"),
        Index(None, "merchant_id", "started_at"),
        Index(
            OPEN_SESSION_CODE_INDEX_NAME,
            "merchant_id",
            "session_code",
            unique=True,
            postgresql_where=text(f"status IN ({sql_member_list(OPEN_SALE_STATUSES)})"),
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchant.id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("product.id"), index=True)
    price_in_paise: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32))
    session_code: Mapped[str] = mapped_column(String(4))
    qr_token_nonce_hash: Mapped[str] = mapped_column(String(64))
    qr_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    qr_token_exchanged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # none_as_null: a sale without a plan stores SQL NULL, not the JSON value null.
    chosen_plan_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSONB(none_as_null=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    request_fingerprint: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
