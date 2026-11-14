"""CheaperModelQuote: a cheaper catalogue item with the plans quoted on its price (an input)."""

from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidEmiTermsError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
)


@dataclass(frozen=True, slots=True)
class CheaperModelQuote:
    """A cheaper model and its priced plans; the catalogue that supplies it belongs to Layer 2."""

    product_id: str
    product_name: str
    price: Money
    priced_offers: tuple[PricedEmiOffer, ...]

    def __post_init__(self) -> None:
        """Refuses blank names, a non-positive price and plans priced on another amount."""
        require_non_empty_text(self.product_id, "product id", InvalidEmiTermsError)
        require_non_empty_text(self.product_name, "product name", InvalidEmiTermsError)
        require_positive_whole_paise_money(self.price, "model price", InvalidEmiTermsError)
        if any(offer.schedule.principal != self.price for offer in self.priced_offers):
            raise InvalidEmiTermsError(
                "Every plan for a cheaper model must be priced on its price."
            )
