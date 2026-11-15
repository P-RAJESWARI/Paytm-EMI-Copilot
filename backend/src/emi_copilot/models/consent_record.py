"""ORM table for the append-only, hash-chained consent records; a trigger rejects any change."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.domain.consent import GENESIS_PREVIOUS_RECORD_HASH
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.models.base import Base, sql_value_list


class ConsentRecordModel(Base):
    """One row per consent; append-only, so there is no updated_at column.

    Unique sale_id allows one consent per sale. Unique chain_position and previous_record_hash
    stop the chain from forking, even for two records racing to be first (the genesis link is a
    fixed value, not NULL). The phone is kept as its last two digits and a keyed hash only.
    """

    __tablename__ = "consent_record"
    __table_args__ = (
        CheckConstraint("chain_position >= 1", name="chain_position_positive"),
        CheckConstraint(
            f"(chain_position = 1) = (previous_record_hash = '{GENESIS_PREVIOUS_RECORD_HASH}')",
            name="genesis_link_only_first",
        ),
        CheckConstraint("phone_last_two_digits ~ '^[0-9]{2}$'", name="phone_last_two_digits_only"),
        CheckConstraint(f"language IN ({sql_value_list(CustomerLanguage)})", name="language_known"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    chain_position: Mapped[int] = mapped_column(BigInteger, unique=True)
    sale_id: Mapped[str] = mapped_column(ForeignKey("sale.id"), unique=True)
    customer_session_id: Mapped[str] = mapped_column(ForeignKey("customer_session.id"), index=True)
    consent_reference: Mapped[str] = mapped_column(String(13))
    plan_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    phone_last_two_digits: Mapped[str] = mapped_column(String(2))
    phone_hash: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(2))
    cooling_off_wording_version: Mapped[str] = mapped_column(String(64))
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_record_hash: Mapped[str] = mapped_column(String(64), unique=True)
    record_hash: Mapped[str] = mapped_column(String(64), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
