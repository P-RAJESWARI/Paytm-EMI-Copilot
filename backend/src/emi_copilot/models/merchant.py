"""ORM table for shops: the pairing PIN only as a scrypt hash and salt, plus its lockout state."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.models.base import Base


class MerchantModel(Base):
    """One row per shop; shop_code is unique and is what the counter device types to pair."""

    __tablename__ = "merchant"
    __table_args__ = (
        CheckConstraint(
            "failed_pin_attempt_count >= 0", name="failed_pin_attempt_count_not_negative"
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    shop_code: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    counter_device_label: Mapped[str] = mapped_column(String(64))
    pin_hash: Mapped[str] = mapped_column(String(64))
    pin_salt: Mapped[str] = mapped_column(String(32))
    failed_pin_attempt_count: Mapped[int] = mapped_column(Integer)
    pin_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
