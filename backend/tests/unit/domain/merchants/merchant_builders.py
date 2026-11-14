"""Builders of valid merchant domain objects with synthetic values; tests override fields."""

from datetime import UTC, datetime, timedelta

from emi_copilot.domain.merchants import UNLOCKED_PIN_ATTEMPT_STATE, DevicePairing, Merchant

PAIRED_AT = datetime(2026, 11, 14, 10, 30, tzinfo=UTC)
SYNTHETIC_TOKEN_HASH = "b" * 64


def build_merchant(**overrides: object) -> Merchant:
    """A synthetic shop with a hex PIN hash and salt, unlocked."""
    fields: dict[str, object] = {
        "id": "01JCMERCHANT00000000000001",
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
        "merchant_id": "01JCMERCHANT00000000000001",
        "device_label": "Counter tablet 1",
        "access_token_hash": SYNTHETIC_TOKEN_HASH,
        "expires_at": PAIRED_AT + timedelta(hours=12),
        "revoked_at": None,
    }
    fields.update(overrides)
    return DevicePairing(**fields)  # type: ignore[arg-type]
