"""GET /api/v1/products with the Mock gateway: offer counts per product, one shop only."""

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.domain.errors import ProductNotFoundError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.product_catalogue_service import ProductCatalogueService
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.merchant_api_helpers import (
    StoredShop,
    pair_and_get_bearer_headers,
    store_demo_catalogue,
    store_shop,
)
from tests.payment_builders import CREATED_AT

pytestmark = pytest.mark.integration

PRODUCTS_PATH = "/api/v1/products"
FIRST_MERCHANT_ID = "01JCMERCHANTPRODUCTS000001"
SECOND_MERCHANT_ID = "01JCMERCHANTPRODUCTS000002"
FIRST_SHOP_PRODUCT_PREFIX = "01JCPRODUCTFIRSTSHOP0000"
SECOND_SHOP_PRODUCT_PREFIX = "01JCPRODUCTSECONDSHOP000"
EXPECTED_FIRST_SHOP_PRODUCTS = [
    {
        "productId": f"{FIRST_SHOP_PRODUCT_PREFIX}02",
        "name": "Example earbuds",
        "listPriceInPaise": 249_900,
        "planCount": 1,
        "noExtraCostPlanCount": 0,
    },
    {
        "productId": f"{FIRST_SHOP_PRODUCT_PREFIX}00",
        "name": "Example phone, 128 GB",
        "listPriceInPaise": 2_200_000,
        "planCount": 3,
        "noExtraCostPlanCount": 1,
    },
    {
        "productId": f"{FIRST_SHOP_PRODUCT_PREFIX}01",
        "name": "Example phone, 64 GB",
        "listPriceInPaise": 1_800_000,
        "planCount": 2,
        "noExtraCostPlanCount": 1,
    },
]


@pytest.fixture
def first_shop(mock_api: ApiHarness) -> StoredShop:
    """Stores the first shop with the three M2 products."""
    shop = store_shop(mock_api, FIRST_MERCHANT_ID, "SHOP-FIRST")
    store_demo_catalogue(mock_api, FIRST_MERCHANT_ID, FIRST_SHOP_PRODUCT_PREFIX)
    return shop


@pytest.fixture
def second_shop(mock_api: ApiHarness) -> StoredShop:
    """Stores a second shop with its own copy of the three products."""
    shop = store_shop(mock_api, SECOND_MERCHANT_ID, "SHOP-SECOND")
    store_demo_catalogue(mock_api, SECOND_MERCHANT_ID, SECOND_SHOP_PRODUCT_PREFIX)
    return shop


def test_products_lists_the_shops_products_with_mock_offer_counts(
    mock_api: ApiHarness, first_shop: StoredShop
) -> None:
    """3 plans (1 no-cost), 2 plans (1 no-cost) and 1 plan, as on the M2 counter list."""
    response = mock_api.client.get(
        PRODUCTS_PATH, headers=pair_and_get_bearer_headers(mock_api, first_shop)
    )
    assert response.status_code == 200
    assert response.json() == {"products": EXPECTED_FIRST_SHOP_PRODUCTS}


@pytest.mark.parametrize(
    ("search_text", "expected_names"),
    [
        ("PHONE", ["Example phone, 128 GB", "Example phone, 64 GB"]),
        ("64 gb", ["Example phone, 64 GB"]),
        ("tablet", []),
    ],
)
def test_products_with_search_keeps_matching_names(
    mock_api: ApiHarness, first_shop: StoredShop, search_text: str, expected_names: list[str]
) -> None:
    """The search ignores case and an empty result is an empty list, not an error."""
    response = mock_api.client.get(
        PRODUCTS_PATH,
        params={"search": search_text},
        headers=pair_and_get_bearer_headers(mock_api, first_shop),
    )
    assert [product["name"] for product in response.json()["products"]] == expected_names


def test_products_never_shows_another_shops_products(
    mock_api: ApiHarness, first_shop: StoredShop, second_shop: StoredShop
) -> None:
    """Each shop sees only its own product ids, though both sell the same items."""
    first_shop_ids = {
        product["productId"]
        for product in mock_api.client.get(
            PRODUCTS_PATH, headers=pair_and_get_bearer_headers(mock_api, first_shop)
        ).json()["products"]
    }
    second_shop_ids = {
        product["productId"]
        for product in mock_api.client.get(
            PRODUCTS_PATH, headers=pair_and_get_bearer_headers(mock_api, second_shop)
        ).json()["products"]
    }
    assert first_shop_ids == {product["productId"] for product in EXPECTED_FIRST_SHOP_PRODUCTS}
    assert all(product_id.startswith(SECOND_SHOP_PRODUCT_PREFIX) for product_id in second_shop_ids)
    assert len(second_shop_ids) == 3


@pytest.mark.usefixtures("first_shop", "second_shop")
def test_get_product_of_another_shop_raises_not_found_on_the_database(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter
) -> None:
    """By-id access is scoped by merchant: the other shop's id looks unknown (404)."""

    def build_unit_of_work() -> SqlAlchemyUnitOfWork:
        """Opens a unit of work on the test database."""
        return SqlAlchemyUnitOfWork(mock_api.session_factory, mock_api.clock)

    catalogue_service = ProductCatalogueService(
        build_unit_of_work,
        OfferDiscoveryService(mock_gateway, build_unit_of_work, mock_api.clock, DomainEventBus()),
    )
    first_shop_principal = MerchantPrincipal(
        merchant_id=FIRST_MERCHANT_ID,
        shop_code="SHOP-FIRST",
        shop_name="Shop SHOP-FIRST",
        device_pairing_id="01JCPAIRINGPRODUCTS0000001",
        device_label="Counter tablet 1",
        access_expires_at=CREATED_AT,
    )
    own_product = catalogue_service.get_product(
        first_shop_principal, f"{FIRST_SHOP_PRODUCT_PREFIX}00"
    )
    assert own_product.name == "Example phone, 128 GB"
    with pytest.raises(ProductNotFoundError):
        catalogue_service.get_product(first_shop_principal, f"{SECOND_SHOP_PRODUCT_PREFIX}00")


def test_products_without_token_returns_401(mock_api: ApiHarness) -> None:
    """The catalogue is a merchant endpoint."""
    response = mock_api.client.get(PRODUCTS_PATH)
    assert response.status_code == 401
    assert response.json()["code"] == "MERCHANT_AUTHENTICATION_REQUIRED"


@pytest.mark.parametrize(
    "query", [{"search": "x" * 65}, {"unexpectedParameter": "x"}], ids=["too-long", "unknown"]
)
def test_products_with_invalid_query_returns_422(
    mock_api: ApiHarness, first_shop: StoredShop, query: dict[str, str]
) -> None:
    """An over-long search or an unknown parameter is refused."""
    response = mock_api.client.get(
        PRODUCTS_PATH, params=query, headers=pair_and_get_bearer_headers(mock_api, first_shop)
    )
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_FAILED"
