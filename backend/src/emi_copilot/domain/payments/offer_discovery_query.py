"""OfferDiscoveryQuery: the item and price for which the gateway is asked to quote EMI offers."""

from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
)


# Pattern: Value Object. A query that exists is complete, so no adapter checks it again.
@dataclass(frozen=True, slots=True)
class OfferDiscoveryQuery:
    """Asks for the EMI offers on one item at one price; the ids are opaque catalogue ids.

    Item-based EMI needs the product, brand and category ids beside the price (ADR 0009). The query
    never holds card or customer data.
    """

    price: Money
    product_id: str
    brand_id: str
    category_id: str

    def __post_init__(self) -> None:
        """Rejects a zero or sub-paise price and any blank identifier."""
        require_positive_whole_paise_money(self.price, "price", InvalidPaymentGatewayValueError)
        for identifier, description in (
            (self.product_id, "product id"),
            (self.brand_id, "brand id"),
            (self.category_id, "category id"),
        ):
            require_non_empty_text(identifier, description, InvalidPaymentGatewayValueError)
