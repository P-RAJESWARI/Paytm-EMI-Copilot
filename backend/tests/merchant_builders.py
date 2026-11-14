"""Builders of valid merchant and catalogue objects with synthetic values; tests override fields."""

from datetime import UTC, datetime, timedelta

from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.merchants import UNLOCKED_PIN_ATTEMPT_STATE, DevicePairing, Merchant
from emi_copilot.domain.money import Money

PAIRED_AT = datetime(2026, 11, 14, 10, 30, tzinfo=UTC)
SYNTHETIC_TOKEN_HASH = "b" * 64
MERCHANT_ID = "01JCMERCHANT00000000000001"
OTHER_MERCHANT_ID = "01JCMERCHANT00000000000002"


def build_merchant(**overrides: object) -> Merchant:
    """A synthetic shop with a hex PIN hash and salt, unlocked."""
    fields: dict[str, object] = {
        "id": MERCHANT_ID,
        "shop_code": "SHOP-0001",
        "display_name": "Synthetic Electronics",
        "counter_device_label": "Counter tablet 1",
        "pin_hash_hex": "c" * 64,
        "pin_salt_hex": "d" * 32,
        "pin_attempt_state": UNLOCKED_PIN_ATTEMPT_STATE,
    }
    fields.update(overrides)
    return Merchant(**fields)  # type: ignore[arg-type]


def build_device_pairing(**overrides: object) -> DevicePairing:
    """A synthetic pairing that expires 12 hours after PAIRED_AT and is not revoked."""
    fields: dict[str, object] = {
        "id": "01JCPAIRING000000000000001",
        "merchant_id": MERCHANT_ID,
        "device_label": "Counter tablet 1",
        "access_token_hash": SYNTHETIC_TOKEN_HASH,
        "expires_at": PAIRED_AT + timedelta(hours=12),
        "revoked_at": None,
    }
    fields.update(overrides)
    return DevicePairing(**fields)  # type: ignore[arg-type]


def build_catalogue_product(**overrides: object) -> CatalogueProduct:
    """A synthetic ₹22,000 product of MERCHANT_ID with synthetic gateway ids."""
    fields: dict[str, object] = {
        "id": "01JCPRODUCT000000000000001",
        "merchant_id": MERCHANT_ID,
        "name": "Example phone, 128 GB",
        "list_price": Money.from_rupees("22000"),
        "gateway_product_id": "product-synthetic-1",
        "gateway_brand_id": "brand-synthetic",
        "gateway_category_id": "category-synthetic",
    }
    fields.update(overrides)
    return CatalogueProduct(**fields)  # type: ignore[arg-type]
