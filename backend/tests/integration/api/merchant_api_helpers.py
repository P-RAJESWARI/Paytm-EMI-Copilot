"""Stores synthetic shops and products for the merchant API tests and pairs their devices."""

from dataclasses import dataclass

from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_EARBUDS_PRODUCT_ID,
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.core.pin_hasher import ScryptPinHasher
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.merchants import UNLOCKED_PIN_ATTEMPT_STATE, Merchant
from emi_copilot.domain.money import Money
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.api.api_harness import ApiHarness

SYNTHETIC_PIN = "135790"
WRONG_PIN = "864209"
PAIRING_PATH = "/api/v1/merchants/pairing"
PIN_HASHER = ScryptPinHasher()


@dataclass(frozen=True, slots=True)
class StoredShop:
    """A shop stored for a test: its id, shop code and the PIN that pairs it."""

    merchant_id: str
    shop_code: str
    pin: str


def store_shop(
    harness: ApiHarness, merchant_id: str, shop_code: str, pin: str = SYNTHETIC_PIN
) -> StoredShop:
    """Commits a shop named after its code whose PIN hashes like the seed's."""
    hashed_pin = PIN_HASHER.hash_new_pin(pin)
    with SqlAlchemyUnitOfWork(harness.session_factory, harness.clock) as unit_of_work:
        unit_of_work.merchants.add(
            Merchant(
                id=merchant_id,
                shop_code=shop_code,
                display_name=f"Shop {shop_code}",
                counter_device_label="Counter tablet 1",
                pin_hash_hex=hashed_pin.hash_hex,
                pin_salt_hex=hashed_pin.salt_hex,
                pin_attempt_state=UNLOCKED_PIN_ATTEMPT_STATE,
            )
        )
    return StoredShop(merchant_id=merchant_id, shop_code=shop_code, pin=pin)


def store_demo_catalogue(harness: ApiHarness, merchant_id: str, id_prefix: str) -> None:
    """Commits the three M2 products for the shop, with the Mock's demo product ids."""
    demo_products = (
        ("Example phone, 128 GB", "22000", MOCK_PHONE_128_GB_PRODUCT_ID),
        ("Example phone, 64 GB", "18000", MOCK_PHONE_64_GB_PRODUCT_ID),
        ("Example earbuds", "2499", MOCK_EARBUDS_PRODUCT_ID),
    )
    with SqlAlchemyUnitOfWork(harness.session_factory, harness.clock) as unit_of_work:
        for index, (name, price_in_rupees, gateway_product_id) in enumerate(demo_products):
            unit_of_work.products.add(
                CatalogueProduct(
                    id=f"{id_prefix}{index:02d}",
                    merchant_id=merchant_id,
                    name=name,
                    list_price=Money.from_rupees(price_in_rupees),
                    gateway_product_id=gateway_product_id,
                    gateway_brand_id="mock-brand-example",
                    gateway_category_id="mock-category-electronics",
                )
            )


def pair_and_get_bearer_headers(harness: ApiHarness, shop: StoredShop) -> dict[str, str]:
    """Pairs a device for the shop and gives the Authorization header its token makes."""
    response = harness.client.post(PAIRING_PATH, json={"shopId": shop.shop_code, "pin": shop.pin})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}
