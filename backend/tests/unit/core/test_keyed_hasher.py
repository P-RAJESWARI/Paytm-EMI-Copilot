"""KeyedHasher: keyed, purpose-separated digests of phone numbers and consent codes."""

import hashlib
import hmac

import pytest

from emi_copilot.core.keyed_hasher import KeyedHasher

SYNTHETIC_KEY = b"synthetic-customer-hash-key-0123456789"  # pragma: allowlist secret
OTHER_SYNTHETIC_KEY = b"other-synthetic-customer-hash-key-012345"  # pragma: allowlist secret
SYNTHETIC_NATIONAL_NUMBER = "9000000042"


def test_phone_hash_is_hmac_sha256_over_the_purpose_label_and_the_number() -> None:
    """Known answer: the digest is HMAC-SHA256 of "customer-phone-number" NUL number."""
    expected_digest = hmac.new(
        SYNTHETIC_KEY, b"customer-phone-number\x009000000042", hashlib.sha256
    ).hexdigest()
    assert KeyedHasher(SYNTHETIC_KEY).hash_customer_phone_number(SYNTHETIC_NATIONAL_NUMBER) == (
        expected_digest
    )


def test_phone_hash_is_stable_for_one_key_and_differs_for_another() -> None:
    """Velocity checks need equal digests under one key; another key gives another digest."""
    first_hasher = KeyedHasher(SYNTHETIC_KEY)
    assert first_hasher.hash_customer_phone_number(SYNTHETIC_NATIONAL_NUMBER) == (
        KeyedHasher(SYNTHETIC_KEY).hash_customer_phone_number(SYNTHETIC_NATIONAL_NUMBER)
    )
    assert first_hasher.hash_customer_phone_number(SYNTHETIC_NATIONAL_NUMBER) != (
        KeyedHasher(OTHER_SYNTHETIC_KEY).hash_customer_phone_number(SYNTHETIC_NATIONAL_NUMBER)
    )


def test_code_hash_is_bound_to_its_challenge_and_never_equals_a_phone_hash() -> None:
    """The fixed Mock code hashes differently per challenge, and purposes never collide."""
    hasher = KeyedHasher(SYNTHETIC_KEY)
    first_digest = hasher.hash_consent_otp_code("challenge-1", "123456")
    assert first_digest == hasher.hash_consent_otp_code("challenge-1", "123456")
    assert first_digest != hasher.hash_consent_otp_code("challenge-2", "123456")
    assert first_digest != hasher.hash_consent_otp_code("challenge-1", "123457")
    assert len(first_digest) == 64
    assert hasher.hash_customer_phone_number("123456") != hasher.hash_consent_otp_code("", "123456")


def test_short_key_is_refused_and_repr_hides_the_key() -> None:
    """A short HMAC key makes digests easier to reverse; the key never appears in repr."""
    with pytest.raises(ValueError, match="at least 32 bytes"):
        KeyedHasher(b"too-short")
    assert SYNTHETIC_KEY.decode() not in repr(KeyedHasher(SYNTHETIC_KEY))
