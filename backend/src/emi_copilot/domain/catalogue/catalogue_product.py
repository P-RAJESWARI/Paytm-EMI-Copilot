"""CatalogueProduct entity: an item a merchant sells, with the ids the gateway quotes EMI on."""

from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
)


@dataclass(frozen=True, slots=True)
class CatalogueProduct:
    """One product of one merchant at its list price; the gateway ids are opaque to us."""

    id: str
    merchant_id: str
    name: str
    list_price: Money
    gateway_product_id: str
    gateway_brand_id: str
    gateway_category_id: str

    def __post_init__(self) -> None:
        """Rejects blank ids or name and a list price that is zero or below one paisa."""
        for text, description in (
            (self.id, "product id"),
            (self.merchant_id, "merchant id"),
            (self.name, "product name"),
            (self.gateway_product_id, "gateway product id"),
            (self.gateway_brand_id, "gateway brand id"),
            (self.gateway_category_id, "gateway category id"),
        ):
            require_non_empty_text(text, description, InvalidMerchantDataError)
        require_positive_whole_paise_money(self.list_price, "list price", InvalidMerchantDataError)

    def to_offer_discovery_query(self) -> OfferDiscoveryQuery:
        """Gives the gateway query for EMI offers on this product at its list price."""
        return OfferDiscoveryQuery(
            price=self.list_price,
            product_id=self.gateway_product_id,
            brand_id=self.gateway_brand_id,
            category_id=self.gateway_category_id,
        )
