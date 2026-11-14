"""Wire schemas of GET /api/v1/products: the merchant's catalogue with offer counts."""

from typing import Annotated

from pydantic import Field

from emi_copilot.dtos.wire_types import (
    CamelCaseQueryModel,
    CamelCaseResponseModel,
    PositiveAmountInPaise,
)
from emi_copilot.services.product_catalogue_service import CatalogueProductWithOffers

MAXIMUM_SEARCH_TEXT_LENGTH = 64


class ProductsQuery(CamelCaseQueryModel):
    """An optional name search over the signed-in merchant's products."""

    search: Annotated[
        str | None,
        Field(
            max_length=MAXIMUM_SEARCH_TEXT_LENGTH,
            description="Keeps products whose name contains this text, ignoring case.",
            examples=["phone"],
        ),
    ] = None


class CatalogueProductResponse(CamelCaseResponseModel):
    """One product at its list price with the counts behind "3 EMI plans, 1 with no extra cost"."""

    product_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0D"])]
    name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    list_price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    plan_count: Annotated[int, Field(ge=0, examples=[3])]
    no_extra_cost_plan_count: Annotated[int, Field(ge=0, examples=[1])]

    @classmethod
    def from_listed_product(cls, listed: CatalogueProductWithOffers) -> "CatalogueProductResponse":
        """Converts one product and its offer summary, with the price in integer paise."""
        return cls(
            product_id=listed.product.id,
            name=listed.product.name,
            list_price_in_paise=listed.product.list_price.to_paise(),
            plan_count=listed.offer_summary.plan_count,
            no_extra_cost_plan_count=listed.offer_summary.no_extra_cost_plan_count,
        )


class ProductsResponse(CamelCaseResponseModel):
    """The merchant's products, dearest first then by name; another shop's never appear."""

    products: list[CatalogueProductResponse]

    @classmethod
    def from_listed_products(
        cls, listed_products: tuple[CatalogueProductWithOffers, ...]
    ) -> "ProductsResponse":
        """Converts the listed products, keeping their order."""
        return cls(
            products=[
                CatalogueProductResponse.from_listed_product(listed) for listed in listed_products
            ]
        )
