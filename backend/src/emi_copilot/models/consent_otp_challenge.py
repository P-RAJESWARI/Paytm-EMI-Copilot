"""ORM table for consent one-time code challenges: the code only as its keyed hash."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.models.base import Base


class ConsentOtpChallengeModel(Base):
    """One row per code sent; (customer_session_id, created_at) finds a session's latest code."""

    __tablename__ = "consent_otp_challenge"
    __table_args__ = (
        CheckConstraint("char_length(code_hash) = 64", name="code_hash_length"),
        CheckConstraint("attempts_remaining >= 0", name="attempts_remaining_not_negative"),
        Index(None, "customer_session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    customer_session_id: Mapped[str] = mapped_column(ForeignKey("customer_session.id"))
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts_remaining: Mapped[int] = mapped_column(SmallInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resend_available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
