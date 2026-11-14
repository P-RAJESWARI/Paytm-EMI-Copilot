"""DemoMerchantSeedService: creates or refreshes the demo shop and its catalogue, idempotently.

Run by `make seed` (scripts/seed_demo_data.py). The PIN always comes from the caller, which
reads it from the environment; it is hashed here and never stored or logged in clear.
"""

from dataclasses import dataclass, field

from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.pin_hasher import ScryptPinHasher
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.merchants import UNLOCKED_PIN_ATTEMPT_STATE, Merchant
from emi_copilot.domain.money import Money
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class DemoProductSeed:
    """One catalogue product to seed; the gateway product id identifies it on a re-run."""

    name: str
    list_price: Money
    gateway_product_id: str
    gateway_brand_id: str
    gateway_category_id: str


@dataclass(frozen=True, slots=True)
class DemoMerchantSeed:
    """The demo shop to seed, its pairing PIN (kept out of repr) and its products."""

    shop_code: str
    display_name: str
    counter_device_label: str
    pin: str = field(repr=False)
    products: tuple[DemoProductSeed, ...]


@dataclass(frozen=True, slots=True)
class DemoMerchantSeedOutcome:
    """What one run did: the shop's id, whether it was new, and how many products it added."""

    merchant_id: str
    is_new_merchant: bool
    added_product_count: int


class DemoMerchantSeedService:
    """Seeds one shop in one transaction; running it again never duplicates anything.

    A new shop is created. An existing shop keeps its id and products, but its names and PIN
    are refreshed and any lockout is cleared, so a changed DEMO_MERCHANT_PIN takes effect.
    Products are matched by gateway product id; missing ones are added, existing ones are kept.
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        pin_hasher: ScryptPinHasher,
        id_generator: IdGenerator,
    ) -> None:
        """Keeps the unit-of-work factory, the PIN hasher and the id generator."""
        self._unit_of_work_factory = unit_of_work_factory
        self._pin_hasher = pin_hasher
        self._id_generator = id_generator

    def seed(self, demo_merchant: DemoMerchantSeed) -> DemoMerchantSeedOutcome:
        """Creates or refreshes the shop, then adds whichever of its products are missing."""
        with self._unit_of_work_factory() as unit_of_work:
            merchant, is_new_merchant = self._create_or_refresh_merchant(
                unit_of_work, demo_merchant
            )
            added_product_count = sum(
                self._add_product_if_missing(unit_of_work, merchant.id, product_seed)
                for product_seed in demo_merchant.products
            )
        return DemoMerchantSeedOutcome(
            merchant_id=merchant.id,
            is_new_merchant=is_new_merchant,
            added_product_count=added_product_count,
        )

    def _create_or_refresh_merchant(
        self, unit_of_work: UnitOfWork, demo_merchant: DemoMerchantSeed
    ) -> tuple[Merchant, bool]:
        """Adds the shop, or updates the stored one; tells whether it was added."""
        hashed_pin = self._pin_hasher.hash_new_pin(demo_merchant.pin)
        stored_merchant = unit_of_work.merchants.find_by_shop_code_for_update(
            demo_merchant.shop_code
        )
        merchant = Merchant(
            id=self._id_generator.new_id() if stored_merchant is None else stored_merchant.id,
            shop_code=demo_merchant.shop_code,
            display_name=demo_merchant.display_name,
            counter_device_label=demo_merchant.counter_device_label,
            pin_hash_hex=hashed_pin.hash_hex,
            pin_salt_hex=hashed_pin.salt_hex,
            pin_attempt_state=UNLOCKED_PIN_ATTEMPT_STATE,
        )
        if stored_merchant is None:
            unit_of_work.merchants.add(merchant)
            return merchant, True
        unit_of_work.merchants.update(merchant)
        return merchant, False

    def _add_product_if_missing(
        self, unit_of_work: UnitOfWork, merchant_id: str, product_seed: DemoProductSeed
    ) -> bool:
        """Adds the product unless the shop already has one with its gateway product id."""
        if (
            unit_of_work.products.find_by_gateway_product_id_for_merchant(
                merchant_id, product_seed.gateway_product_id
            )
            is not None
        ):
            return False
        unit_of_work.products.add(
            CatalogueProduct(
                id=self._id_generator.new_id(),
                merchant_id=merchant_id,
                name=product_seed.name,
                list_price=product_seed.list_price,
                gateway_product_id=product_seed.gateway_product_id,
                gateway_brand_id=product_seed.gateway_brand_id,
                gateway_category_id=product_seed.gateway_category_id,
            )
        )
        return True
