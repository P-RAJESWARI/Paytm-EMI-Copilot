"""In-memory merchant, device pairing and product repositories for service tests."""

from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.merchants import DevicePairing, Merchant


class FakeMerchantRepository:
    """Holds merchants in a dict and enforces the unique shop code like the database does."""

    def __init__(self, merchants_by_id: dict[str, Merchant]) -> None:
        """Works on the unit of work's private copy of the merchants."""
        self._merchants_by_id = merchants_by_id

    def add(self, merchant: Merchant) -> None:
        """Stores a new merchant; a duplicate id or shop code fails as the constraint would."""
        if any(
            stored.id == merchant.id or stored.shop_code == merchant.shop_code
            for stored in self._merchants_by_id.values()
        ):
            raise InvalidMerchantDataError("A merchant with this id or shop code exists (fake).")
        self._merchants_by_id[merchant.id] = merchant

    def find_by_id(self, merchant_id: str) -> Merchant | None:
        """Returns the merchant with the id, or None."""
        return self._merchants_by_id.get(merchant_id)

    def find_by_shop_code_for_update(self, shop_code: str) -> Merchant | None:
        """Returns the merchant with the shop code; a single-threaded fake needs no lock."""
        return next(
            (
                merchant
                for merchant in self._merchants_by_id.values()
                if merchant.shop_code == shop_code
            ),
            None,
        )

    def lock_for_update(self, merchant_id: str) -> None:
        """Does nothing: a single-threaded fake has no concurrent sale starts to serialise."""

    def update(self, merchant: Merchant) -> None:
        """Replaces a stored merchant; an unknown one fails as the real repository does."""
        if merchant.id not in self._merchants_by_id:
            raise InvalidMerchantDataError("No such merchant (fake).")
        self._merchants_by_id[merchant.id] = merchant


class FakeDevicePairingRepository:
    """Holds pairings in a dict keyed by id; the token hash is unique as in the database."""

    def __init__(self, device_pairings_by_id: dict[str, DevicePairing]) -> None:
        """Works on the unit of work's private copy of the pairings."""
        self._device_pairings_by_id = device_pairings_by_id

    def add(self, device_pairing: DevicePairing) -> None:
        """Stores a new pairing; a duplicate token hash fails as the constraint would."""
        if self.find_by_access_token_hash(device_pairing.access_token_hash) is not None:
            raise InvalidMerchantDataError("A pairing with this token hash exists (fake).")
        self._device_pairings_by_id[device_pairing.id] = device_pairing

    def find_by_access_token_hash(self, access_token_hash: str) -> DevicePairing | None:
        """Returns the pairing with the token hash, or None."""
        return next(
            (
                pairing
                for pairing in self._device_pairings_by_id.values()
                if pairing.access_token_hash == access_token_hash
            ),
            None,
        )


class FakeProductRepository:
    """Holds products in a dict and filters every read by merchant id, like the real one."""

    def __init__(self, products_by_id: dict[str, CatalogueProduct]) -> None:
        """Works on the unit of work's private copy of the products."""
        self._products_by_id = products_by_id

    def add(self, product: CatalogueProduct) -> None:
        """Stores a new product."""
        self._products_by_id[product.id] = product

    def list_for_merchant(
        self, merchant_id: str, name_search_text: str | None = None
    ) -> tuple[CatalogueProduct, ...]:
        """Lists the merchant's products by name then id; the search ignores case."""
        matching_products = [
            product
            for product in self._products_by_id.values()
            if product.merchant_id == merchant_id
            and (not name_search_text or name_search_text.lower() in product.name.lower())
        ]
        return tuple(sorted(matching_products, key=lambda product: (product.name, product.id)))

    def find_by_id_for_merchant(self, merchant_id: str, product_id: str) -> CatalogueProduct | None:
        """Returns the product only if it belongs to the merchant."""
        product = self._products_by_id.get(product_id)
        return product if product is not None and product.merchant_id == merchant_id else None

    def find_by_gateway_product_id_for_merchant(
        self, merchant_id: str, gateway_product_id: str
    ) -> CatalogueProduct | None:
        """Returns the merchant's product with the gateway product id, or None."""
        return next(
            (
                product
                for product in self.list_for_merchant(merchant_id)
                if product.gateway_product_id == gateway_product_id
            ),
            None,
        )
