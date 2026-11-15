"""ORM table for customer sessions: the token only as its hash, the budget in integer paise."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.domain.customer_sessions import ComfortCheckStatus, CustomerLanguage
from emi_copilot.models.base import Base, sql_value_list


class CustomerSessionModel(Base):
    """One row per QR exchange; a session is found by its unique token hash, never its token.

    It holds the confirmed budget and the comfort check choice only, never income or EMIs.
    """

    __tablename__ = "customer_session"
    __table_args__ = (
        CheckConstraint("char_length(token_hash) = 64", name="token_hash_length"),
        CheckConstraint("monthly_budget_in_paise > 0", name="monthly_budget_in_paise_positive"),
        CheckConstraint(
            f"comfort_check_status IN ({sql_value_list(ComfortCheckStatus)})",
            name="comfort_check_status_known",
        ),
        CheckConstraint(f"language IN ({sql_value_list(CustomerLanguage)})", name="language_known"),
        CheckConstraint("expires_at > created_at", name="expires_after_start"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    sale_id: Mapped[str] = mapped_column(ForeignKey("sale.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    monthly_budget_in_paise: Mapped[int | None] = mapped_column(BigInteger)
    comfort_check_status: Mapped[str] = mapped_column(String(16))
    language: Mapped[str | None] = mapped_column(String(2))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
