"""Two paired shops with the M2 catalogue, and helpers to start and agree sales via the API."""

from dataclasses import dataclass
from datetime import timedelta

from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.merchant_api_helpers import (
    pair_and_get_bearer_headers,
    store_demo_catalogue,
    store_shop,
)
from tests.payment_builders import CREATED_AT
from tests.sale_builders import build_no_cost_chosen_plan

SALES_PATH = "/api/v1/sales"
COUNTER_PATH = f"{SALES_PATH}?view=counter"
FIRST_SHOP_PRODUCT_PREFIX = "01JCPRODUCTSALESHOPA0000"
SECOND_SHOP_PRODUCT_PREFIX = "01JCPRODUCTSALESHOPB0000"
PHONE_128_GB_ID = f"{FIRST_SHOP_PRODUCT_PREFIX}00"
PHONE_64_GB_ID = f"{FIRST_SHOP_PRODUCT_PREFIX}01"
SECOND_SHOP_PHONE_ID = f"{SECOND_SHOP_PRODUCT_PREFIX}00"
SALE_DETAIL_KEYS = {
    "saleId",
    "sessionCode",
    "productName",
    "priceInPaise",
    "status",
    "statusChangedAt",
    "chosenPlan",
    "productId",
    "startedAt",
    "qr",
}
QR_EXPIRES_AT = (CREATED_AT + timedelta(minutes=15)).replace(microsecond=0)


@dataclass(frozen=True, slots=True)
class TwoShops:
    """Bearer headers of two paired shops, each with the three M2 products."""

    first_shop_headers: dict[str, str]
    second_shop_headers: dict[str, str]


def store_and_pair_two_shops(mock_api: ApiHarness) -> TwoShops:
    """Stores and pairs two shops with their own catalogues."""
    first_shop = store_shop(mock_api, "01JCMERCHANTSALES000000001", "SHOP-SALES-A")
    second_shop = store_shop(mock_api, "01JCMERCHANTSALES000000002", "SHOP-SALES-B")
    store_demo_catalogue(mock_api, first_shop.merchant_id, FIRST_SHOP_PRODUCT_PREFIX)
    store_demo_catalogue(mock_api, second_shop.merchant_id, SECOND_SHOP_PRODUCT_PREFIX)
    return TwoShops(
        first_shop_headers=pair_and_get_bearer_headers(mock_api, first_shop),
        second_shop_headers=pair_and_get_bearer_headers(mock_api, second_shop),
    )


def start_sale(
    harness: ApiHarness, headers: dict[str, str], product_id: str = PHONE_128_GB_ID
) -> dict[str, object]:
    """Starts a sale through the API and gives its JSON body."""
    response = harness.client.post(SALES_PATH, json={"productId": product_id}, headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def mark_ready_to_pay_in_the_database(harness: ApiHarness, sale_id: str) -> None:
    """Moves a sale to READY_TO_PAY on plan A directly, as Layer 3 consent will."""
    with SqlAlchemyUnitOfWork(harness.session_factory, harness.clock) as unit_of_work:
        sale = unit_of_work.sales.find_by_id_for_update(sale_id)
        assert sale is not None
        unit_of_work.sales.update(
            sale.agree_to_plan(build_no_cost_chosen_plan(), harness.clock.now())
        )
