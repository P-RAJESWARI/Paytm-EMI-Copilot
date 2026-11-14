"""Tests for the Merchant and DevicePairing entities."""

from datetime import datetime, timedelta

import pytest

from emi_copilot.domain.errors import InvalidMerchantDataError
from tests.unit.domain.merchants.merchant_builders import (
    PAIRED_AT,
    build_device_pairing,
    build_merchant,
)


def test_merchant_with_valid_fields_keeps_them() -> None:
    """A complete shop is built as given."""
    merchant = build_merchant(shop_code="RAVI-0193")
    assert merchant.shop_code == "RAVI-0193"
    assert merchant.counter_device_label == "Counter tablet 1"


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("id", ""),
        ("display_name", "  "),
        ("counter_device_label", ""),
        ("shop_code", "ravi-0193"),
        ("shop_code", "-RAVI"),
        ("shop_code", "R" * 33),
        ("shop_code", 193),
        ("pin_hash_hex", "NOT-HEX"),
        ("pin_salt_hex", ""),
        ("pin_hash_hex", None),
    ],
)
def test_merchant_with_invalid_field_raises(field_name: str, invalid_value: object) -> None:
    """Blank names, a lower-case or over-long shop code and a non-hex hash are refused."""
    with pytest.raises(InvalidMerchantDataError):
        build_merchant(**{field_name: invalid_value})


def test_device_pairing_is_usable_until_just_before_it_expires() -> None:
    """The expiry moment itself no longer signs the device in."""
    pairing = build_device_pairing()
    assert pairing.is_usable_at(PAIRED_AT) is True
    assert pairing.is_usable_at(pairing.expires_at - timedelta(microseconds=1)) is True
    assert pairing.is_usable_at(pairing.expires_at) is False


def test_device_pairing_once_revoked_is_never_usable() -> None:
    """A revoked pairing is refused even before it would expire."""
    pairing = build_device_pairing(revoked_at=PAIRED_AT)
    assert pairing.is_usable_at(PAIRED_AT) is False


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("id", ""),
        ("merchant_id", " "),
        ("device_label", ""),
        ("access_token_hash", "B" * 64),
        ("access_token_hash", "b" * 63),
        ("access_token_hash", None),
        ("expires_at", datetime(2026, 11, 14, 22, 30)),  # noqa: DTZ001 - naive on purpose
        ("revoked_at", datetime(2026, 11, 14, 11, 0)),  # noqa: DTZ001 - naive on purpose
    ],
)
def test_device_pairing_with_invalid_field_raises(field_name: str, invalid_value: object) -> None:
    """Blank ids, a malformed hash or naive timestamps are refused."""
    with pytest.raises(InvalidMerchantDataError):
        build_device_pairing(**{field_name: invalid_value})
