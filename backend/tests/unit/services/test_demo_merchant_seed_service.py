"""DemoMerchantSeedService: seeding twice gives one shop, its products once and the new PIN."""

from dataclasses import replace

import pytest

from emi_copilot.core.pin_hasher import HashedPin, ScryptPinHasher
from emi_copilot.domain.merchants import UNLOCKED_PIN_ATTEMPT_STATE, PinAttemptState
from emi_copilot.domain.money import Money
from emi_copilot.services.demo_merchant_seed_service import (
    DemoMerchantSeed,
    DemoMerchantSeedOutcome,
    DemoMerchantSeedService,
    DemoProductSeed,
)
from tests.payment_builders import CREATED_AT
from tests.unit.services.conftest import ServiceTestKit

FIRST_PIN = "135790"
SECOND_PIN = "246801"
PHONE_SEED = DemoProductSeed(
    name="Example phone, 128 GB",
    list_price=Money.from_rupees("22000"),
    gateway_product_id="product-synthetic-1",
    gateway_brand_id="brand-synthetic",
    gateway_category_id="category-synthetic",
)
EARBUDS_SEED = DemoProductSeed(
    name="Example earbuds",
    list_price=Money.from_rupees("2499"),
    gateway_product_id="product-synthetic-2",
    gateway_brand_id="brand-synthetic",
    gateway_category_id="category-synthetic",
)


def build_seed(pin: str = FIRST_PIN, **overrides: object) -> DemoMerchantSeed:
    """A synthetic shop seed with two products."""
    fields: dict[str, object] = {
        "shop_code": "SHOP-SEED",
        "display_name": "Synthetic Seeded Shop",
        "counter_device_label": "Counter tablet 1",
        "pin": pin,
        "products": (PHONE_SEED, EARBUDS_SEED),
    }
    fields.update(overrides)
    return DemoMerchantSeed(**fields)  # type: ignore[arg-type]


@pytest.fixture(scope="module")
def pin_hasher() -> ScryptPinHasher:
    """Builds one real hasher for the module."""
    return ScryptPinHasher()


@pytest.fixture
def service(kit: ServiceTestKit, pin_hasher: ScryptPinHasher) -> DemoMerchantSeedService:
    """Builds the seed service on the in-memory database."""
    return DemoMerchantSeedService(kit.unit_of_work_factory, pin_hasher, kit.id_generator)


def test_seed_on_empty_database_creates_the_shop_with_hashed_pin_and_products(
    service: DemoMerchantSeedService, kit: ServiceTestKit, pin_hasher: ScryptPinHasher
) -> None:
    """The shop is new, both products are added and only the PIN's hash is stored."""
    outcome = service.seed(build_seed())
    (merchant,) = kit.database.merchants_by_id.values()
    assert outcome == DemoMerchantSeedOutcome(
        merchant_id=merchant.id, is_new_merchant=True, added_product_count=2
    )
    assert merchant.shop_code == "SHOP-SEED"
    assert FIRST_PIN not in repr(merchant)
    assert pin_hasher.is_matching_pin(
        FIRST_PIN, HashedPin(hash_hex=merchant.pin_hash_hex, salt_hex=merchant.pin_salt_hex)
    )
    assert sorted(product.name for product in kit.database.products_by_id.values()) == [
        "Example earbuds",
        "Example phone, 128 GB",
    ]
    assert {product.merchant_id for product in kit.database.products_by_id.values()} == {
        merchant.id
    }


def test_seed_run_twice_keeps_one_shop_and_one_copy_of_each_product(
    service: DemoMerchantSeedService, kit: ServiceTestKit
) -> None:
    """A second run adds nothing and keeps the shop's id."""
    first_outcome = service.seed(build_seed())
    second_outcome = service.seed(build_seed())
    assert second_outcome == DemoMerchantSeedOutcome(
        merchant_id=first_outcome.merchant_id, is_new_merchant=False, added_product_count=0
    )
    assert len(kit.database.merchants_by_id) == 1
    assert len(kit.database.products_by_id) == 2


def test_seed_again_with_new_pin_and_names_refreshes_them_and_clears_a_lock(
    service: DemoMerchantSeedService, kit: ServiceTestKit, pin_hasher: ScryptPinHasher
) -> None:
    """A changed DEMO_MERCHANT_PIN takes effect, and a locked demo shop is unlocked."""
    outcome = service.seed(build_seed())
    stored_merchant = kit.database.merchants_by_id[outcome.merchant_id]
    kit.database.merchants_by_id[outcome.merchant_id] = replace(
        stored_merchant,
        pin_attempt_state=PinAttemptState(consecutive_failure_count=0, locked_until=CREATED_AT),
    )
    service.seed(build_seed(pin=SECOND_PIN, display_name="Renamed Shop"))
    refreshed_merchant = kit.database.merchants_by_id[outcome.merchant_id]
    stored_pin = HashedPin(
        hash_hex=refreshed_merchant.pin_hash_hex, salt_hex=refreshed_merchant.pin_salt_hex
    )
    assert pin_hasher.is_matching_pin(SECOND_PIN, stored_pin)
    assert not pin_hasher.is_matching_pin(FIRST_PIN, stored_pin)
    assert refreshed_merchant.display_name == "Renamed Shop"
    assert refreshed_merchant.pin_attempt_state == UNLOCKED_PIN_ATTEMPT_STATE


def test_seed_again_with_an_extra_product_adds_only_that_product(
    service: DemoMerchantSeedService, kit: ServiceTestKit
) -> None:
    """Products are matched by gateway product id, so a new one is added alone."""
    service.seed(build_seed(products=(PHONE_SEED,)))
    outcome = service.seed(build_seed())
    assert outcome.added_product_count == 1
    assert len(kit.database.products_by_id) == 2


def test_demo_merchant_seed_repr_hides_the_pin() -> None:
    """A seed that ends up in a log or traceback never shows the PIN."""
    assert FIRST_PIN not in repr(build_seed())
