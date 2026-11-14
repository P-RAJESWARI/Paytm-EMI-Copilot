"""ORM table for paired counter devices; a bearer token is stored only as its SHA-256 hash."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.models.base import Base


class DevicePairingModel(Base):
    """One row per paired device; the token hash is unique and indexed for sign-in lookups."""

    __tablename__ = "device_pairing"
    __table_args__ = (
        CheckConstraint("char_length(access_token_hash) = 64", name="access_token_hash_length"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchant.id"), index=True)
    device_label: Mapped[str] = mapped_column(String(64))
    access_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
