"""Wire schemas of GET /api/v1/offers: the item query and the priced EMI offers it returns."""

from typing import Annotated

from pydantic import Field

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType, OfferDiscoveryQuery, PricedEmiOffer
from emi_copilot.dtos.wire_types import (
    CamelCaseQueryModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    OpaqueIdentifier,
    PositiveAmountInPaise,
)

SAMPLE_PRICE_IN_PAISE = 2_200_000


class OffersQuery(CamelCaseQueryModel):
    """The item and price to quote EMI offers for; item-based EMI needs all four (ADR 0009)."""

    price_in_paise: Annotated[
        PositiveAmountInPaise,
        Field(description="Item price in paise.", examples=[SAMPLE_PRICE_IN_PAISE]),
    ]
    product_id: Annotated[
        OpaqueIdentifier, Field(description="Catalogue product id.", examples=["product-tv-43"])
    ]
    brand_id: Annotated[
        OpaqueIdentifier, Field(description="Catalogue brand id.", examples=["brand-demo"])
    ]
    category_id: Annotated[
        OpaqueIdentifier,
        Field(description="Catalogue category id.", examples=["category-televisions"]),
    ]

    def to_offer_discovery_query(self) -> OfferDiscoveryQuery:
        """Gives the domain query for this item, with the price as Money."""
        return OfferDiscoveryQuery(
            price=Money.from_paise(self.price_in_paise),
            product_id=self.product_id,
            brand_id=self.brand_id,
            category_id=self.category_id,
        )


class EmiOfferResponse(CamelCaseResponseModel):
    """One EMI plan: the lender's monthly figure beside our exact schedule totals (ADR 0001).

    monthlyInstallmentInPaise is the lender's quoted figure. The other amounts come from our
    schedule: the remainder sits on the last installment, so the installments add up to
    totalPayableInPaise exactly.
    """

    offer_id: Annotated[str, Field(examples=["mock-offer-card-6m"])]
    lender_label: Annotated[str, Field(examples=["Your card's bank"])]
    emi_type: EmiType
    tenure_in_months: Annotated[int, Field(ge=1, examples=[6])]
    monthly_installment_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[385_000])]
    last_installment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[385_000])]
    extra_in_total_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[110_000])]
    total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_310_000])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[SAMPLE_PRICE_IN_PAISE])]

    @classmethod
    def from_priced_offer(cls, priced_offer: PricedEmiOffer) -> "EmiOfferResponse":
        """Converts one priced offer to integer paise for the wire."""
        schedule = priced_offer.schedule
        return cls(
            offer_id=priced_offer.offer.offer_id,
            lender_label=priced_offer.offer.lender_label,
            emi_type=priced_offer.offer.emi_type,
            tenure_in_months=priced_offer.offer.tenure_in_months,
            monthly_installment_in_paise=priced_offer.quoted_monthly_installment.to_paise(),
            last_installment_in_paise=schedule.last_installment.to_paise(),
            extra_in_total_in_paise=schedule.extra_in_total.to_paise(),
            total_payable_in_paise=schedule.total_payable.to_paise(),
            price_in_paise=schedule.principal.to_paise(),
        )


class OffersResponse(CamelCaseResponseModel):
    """Every offer the gateway quotes for the item, in the gateway's order; none is hidden."""

    offers: list[EmiOfferResponse]

    @classmethod
    def from_priced_offers(cls, priced_offers: tuple[PricedEmiOffer, ...]) -> "OffersResponse":
        """Converts the priced offers, keeping their order."""
        return cls(offers=[EmiOfferResponse.from_priced_offer(offer) for offer in priced_offers])
