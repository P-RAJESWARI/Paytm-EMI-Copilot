"""ORM table for each merchant's catalogue: list price in integer paise, gateway ids opaque."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from emi_copilot.models.base import Base


class ProductModel(Base):
    """One row per product of one merchant; every query filters on merchant_id."""

    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint("list_price_in_paise > 0", name="list_price_in_paise_positive"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchant.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    gateway_product_id: Mapped[str] = mapped_column(String(128))
    gateway_brand_id: Mapped[str] = mapped_column(String(128))
    gateway_category_id: Mapped[str] = mapped_column(String(128))
    list_price_in_paise: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
