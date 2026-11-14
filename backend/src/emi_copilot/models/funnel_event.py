"""ORM table for the append-only funnel; a database trigger rejects UPDATE, DELETE and TRUNCATE."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.models.base import Base, sql_value_list


class FunnelEventModel(Base):
    """One row per (sale, stage); append-only, so there is no updated_at column.

    The (sale_id, stage) unique constraint also indexes sale_id, and (merchant_id, occurred_at)
    indexes merchant_id for the report queries.
    """

    __tablename__ = "funnel_event"
    __table_args__ = (
        CheckConstraint(f"stage IN ({sql_value_list(FunnelStage)})", name="stage_known"),
        CheckConstraint(
            "(monthly_budget_in_paise IS NOT NULL) = (stage = 'BUDGET_TOLD')",
            name="monthly_budget_only_on_budget_told",
        ),
        CheckConstraint("monthly_budget_in_paise > 0", name="monthly_budget_in_paise_positive"),
        UniqueConstraint("sale_id", "stage"),
        Index(None, "merchant_id", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    sale_id: Mapped[str] = mapped_column(ForeignKey("sale.id"))
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchant.id"))
    stage: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    monthly_budget_in_paise: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
