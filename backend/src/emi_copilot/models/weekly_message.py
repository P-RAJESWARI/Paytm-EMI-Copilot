"""ORM table recording that one shop's weekly message for one week was sent (plan Q14)."""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.models.base import Base


class WeeklyMessageModel(Base):
    """One row per shop and week, written once when the message is sent; the text is not stored.

    The text is rebuilt from the report numbers on every read. The (merchant_id,
    period_start_date) unique constraint makes sending idempotent and also indexes merchant_id.
    """

    __tablename__ = "weekly_message"
    __table_args__ = (
        UniqueConstraint("merchant_id", "period_start_date"),
        CheckConstraint(
            "EXTRACT(ISODOW FROM period_start_date) = 1", name="period_start_date_is_monday"
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchant.id"))
    period_start_date: Mapped[date] = mapped_column(Date)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
