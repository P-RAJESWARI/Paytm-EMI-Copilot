"""GET /api/v1/products: the signed-in merchant's catalogue with EMI offer counts (M2)."""

from typing import Annotated

from fastapi import APIRouter, Query

from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.merchant_dependencies import ProductCatalogueServiceDependency
from emi_copilot.api.openapi_documentation import (
    GATEWAY_FAILURE_PROBLEMS,
    GATEWAY_TIMEOUT_PROBLEM,
    MERCHANT_AUTHENTICATION_PROBLEM,
    MERCHANT_BEARER_NOTE,
    REQUEST_VALIDATION_PROBLEM,
    describe_problem_responses,
)
from emi_copilot.dtos.product_dtos import ProductsQuery, ProductsResponse

product_router = APIRouter(tags=["products"])

PRODUCTS_RESPONSE_EXAMPLE = {
    "products": [
        {
            "productId": "01JD5Z0Q8M6X3V2N7B4C9K1T0D",
            "name": "Example phone, 128 GB",
            "listPriceInPaise": 2_200_000,
            "planCount": 3,
            "noExtraCostPlanCount": 1,
        },
        {
            "productId": "01JD5Z0Q8M6X3V2N7B4C9K1T0E",
            "name": "Example earbuds",
            "listPriceInPaise": 249_900,
            "planCount": 1,
            "noExtraCostPlanCount": 0,
        },
    ]
}


@product_router.get(
    "/products",
    summary="List the shop's products with their EMI offer counts",
    description=(
        "Lists the signed-in shop's products, highest list price first and then by name, "
        "optionally narrowed by a name search, "
        "each at its list price with how many EMI plans the gateway quotes now and how many of "
        "those cost nothing extra. The counts come from the same offer discovery as GET "
        "/api/v1/offers; a gateway failure on any product fails the list. " + MERCHANT_BEARER_NOTE
    ),
    response_description="The shop's products, highest list price first.",
    responses={
        200: {"content": {"application/json": {"example": PRODUCTS_RESPONSE_EXAMPLE}}},
        **describe_problem_responses(
            REQUEST_VALIDATION_PROBLEM,
            MERCHANT_AUTHENTICATION_PROBLEM,
            *GATEWAY_FAILURE_PROBLEMS,
            GATEWAY_TIMEOUT_PROBLEM,
        ),
    },
)
def list_products(
    products_query: Annotated[ProductsQuery, Query()],
    current_merchant: CurrentMerchant,
    product_catalogue_service: ProductCatalogueServiceDependency,
) -> ProductsResponse:
    """Lists the signed-in shop's products for the search and converts them to paise."""
    listed_products = product_catalogue_service.list_products(
        current_merchant, products_query.search
    )
    return ProductsResponse.from_listed_products(listed_products)
