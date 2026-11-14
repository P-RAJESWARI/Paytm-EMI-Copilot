"""Stores and loads catalogue products; every read is scoped to one merchant."""

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.money import Money
from emi_copilot.models import ProductModel


def _to_domain(product_model: ProductModel) -> CatalogueProduct:
    """Maps an ORM row back to a validated domain entity, with the price as Money."""
    return CatalogueProduct(
        id=product_model.id,
        merchant_id=product_model.merchant_id,
        name=product_model.display_name,
        list_price=Money.from_paise(product_model.list_price_in_paise),
        gateway_product_id=product_model.gateway_product_id,
        gateway_brand_id=product_model.gateway_brand_id,
        gateway_category_id=product_model.gateway_category_id,
    )


# Pattern: Repository. No read without a merchant id exists, so one shop never sees another's.
class ProductRepository:
    """Adds products and lists or finds them for one merchant only."""

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for created_at and updated_at."""
        self._session = session
        self._clock = clock

    def add(self, product: CatalogueProduct) -> None:
        """Inserts a new product now, with its list price as integer paise."""
        now = self._clock.now()
        self._session.add(
            ProductModel(
                id=product.id,
                merchant_id=product.merchant_id,
                display_name=product.name,
                gateway_product_id=product.gateway_product_id,
                gateway_brand_id=product.gateway_brand_id,
                gateway_category_id=product.gateway_category_id,
                list_price_in_paise=product.list_price.to_paise(),
                created_at=now,
                updated_at=now,
            )
        )
        self._session.flush()

    def list_for_merchant(
        self, merchant_id: str, name_search_text: str | None = None
    ) -> tuple[CatalogueProduct, ...]:
        """Lists the merchant's products dearest first, then by name and id, as M2 shows them.

        A search keeps names containing it.

        The search ignores case and treats % and _ as plain characters, not SQL wildcards.
        """
        statement = select(ProductModel).where(ProductModel.merchant_id == merchant_id)
        if name_search_text:
            statement = statement.where(
                ProductModel.display_name.icontains(name_search_text, autoescape=True)
            )
        product_models = self._session.scalars(
            statement.order_by(
                ProductModel.list_price_in_paise.desc(), ProductModel.display_name, ProductModel.id
            )
        ).all()
        return tuple(_to_domain(product_model) for product_model in product_models)

    def find_by_id_for_merchant(self, merchant_id: str, product_id: str) -> CatalogueProduct | None:
        """Returns the product only if it belongs to the merchant; another shop's gives None."""
        return self._find_one_for_merchant(merchant_id, ProductModel.id == product_id)

    def find_by_gateway_product_id_for_merchant(
        self, merchant_id: str, gateway_product_id: str
    ) -> CatalogueProduct | None:
        """Returns the merchant's first product with this gateway product id, or None."""
        return self._find_one_for_merchant(
            merchant_id, ProductModel.gateway_product_id == gateway_product_id
        )

    def _find_one_for_merchant(
        self, merchant_id: str, condition: ColumnElement[bool]
    ) -> CatalogueProduct | None:
        """Loads the first of the merchant's products, by id, that matches a condition."""
        product_model = self._session.scalars(
            select(ProductModel)
            .where((ProductModel.merchant_id == merchant_id) & condition)
            .order_by(ProductModel.id)
            .limit(1)
        ).one_or_none()
        return None if product_model is None else _to_domain(product_model)
