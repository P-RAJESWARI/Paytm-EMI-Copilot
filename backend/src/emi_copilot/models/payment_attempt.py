"""ORM table for payment attempts: money in integer paise, no card fields, no personal data."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.domain.payments import PaymentAttemptStatus
from emi_copilot.models.base import Base, sql_value_list


class PaymentAttemptModel(Base):
    """One row per payment attempt; order_id and idempotency_key are each unique (ADR 0005)."""

    __tablename__ = "payment_attempt"
    __table_args__ = (
        CheckConstraint("amount_in_paise > 0", name="amount_in_paise_positive"),
        CheckConstraint(f"status IN ({sql_value_list(PaymentAttemptStatus)})", name="status_known"),
        CheckConstraint("char_length(request_fingerprint) = 64", name="request_fingerprint_length"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    amount_in_paise: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32))
    offer_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    gateway_mode: Mapped[str] = mapped_column(String(16))
    gateway_link_id: Mapped[str | None] = mapped_column(String(128))
    payment_link_url: Mapped[str | None] = mapped_column(String(2048))
    gateway_transaction_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
