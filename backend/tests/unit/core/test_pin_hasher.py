"""Tests for salted scrypt PIN hashing and its constant-time check."""

import hashlib

import pytest

from emi_copilot.core import pin_hasher
from emi_copilot.core.pin_hasher import HashedPin, ScryptPinHasher

SYNTHETIC_PIN = "135790"
KNOWN_ANSWER_SALT_HEX = bytes(range(16)).hex()
# scrypt(N=2^14, r=8, p=1, 32 bytes) of the synthetic PIN with salt 00 01 ... 0f.
KNOWN_ANSWER_HASH_HEX = (
    "3a9d0dcd32b4ef29b623be93178ba0e899256230028bfae00151f40231f5b6bb"  # pragma: allowlist secret
)


@pytest.fixture(scope="module")
def hasher() -> ScryptPinHasher:
    """Builds one hasher for the module; its decoy hash costs one scrypt run."""
    return ScryptPinHasher()


def test_is_matching_pin_with_known_answer_vector_returns_true(hasher: ScryptPinHasher) -> None:
    """The stored form is scrypt with the documented parameters, so it is reproducible."""
    known_answer = HashedPin(hash_hex=KNOWN_ANSWER_HASH_HEX, salt_hex=KNOWN_ANSWER_SALT_HEX)
    assert hasher.is_matching_pin(SYNTHETIC_PIN, known_answer) is True


def test_known_answer_vector_matches_the_standard_library_scrypt() -> None:
    """The vector is plain RFC 7914 scrypt, not a home-made construction."""
    derived_hash = hashlib.scrypt(
        SYNTHETIC_PIN.encode("utf-8"), salt=bytes(range(16)), n=2**14, r=8, p=1, dklen=32
    )
    assert derived_hash.hex() == KNOWN_ANSWER_HASH_HEX


@pytest.mark.parametrize("wrong_pin", ["135791", "035790", "13579", "1357900", ""])
def test_is_matching_pin_with_wrong_pin_returns_false(
    hasher: ScryptPinHasher, wrong_pin: str
) -> None:
    """One changed, missing or extra digit fails the check."""
    known_answer = HashedPin(hash_hex=KNOWN_ANSWER_HASH_HEX, salt_hex=KNOWN_ANSWER_SALT_HEX)
    assert hasher.is_matching_pin(wrong_pin, known_answer) is False


def test_hash_new_pin_round_trips_and_uses_a_fresh_salt_each_time(
    hasher: ScryptPinHasher,
) -> None:
    """Two hashes of one PIN differ (new salt), yet each verifies the PIN."""
    first_hash = hasher.hash_new_pin(SYNTHETIC_PIN)
    second_hash = hasher.hash_new_pin(SYNTHETIC_PIN)
    assert first_hash.salt_hex != second_hash.salt_hex
    assert first_hash.hash_hex != second_hash.hash_hex
    assert len(first_hash.salt_hex) == 2 * pin_hasher.SALT_LENGTH_IN_BYTES
    assert len(first_hash.hash_hex) == 2 * pin_hasher.HASH_LENGTH_IN_BYTES
    assert hasher.is_matching_pin(SYNTHETIC_PIN, first_hash) is True
    assert hasher.is_matching_pin(SYNTHETIC_PIN, second_hash) is True


def test_is_matching_pin_compares_in_constant_time(
    hasher: ScryptPinHasher, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final comparison goes through hmac.compare_digest, never ==."""
    compared_pairs: list[tuple[bytes, bytes]] = []

    def recording_compare_digest(first: bytes, second: bytes) -> bool:
        """Records the compared values and answers as the real function would."""
        compared_pairs.append((first, second))
        return first == second

    monkeypatch.setattr("emi_copilot.core.pin_hasher.hmac.compare_digest", recording_compare_digest)
    hasher.is_matching_pin(
        SYNTHETIC_PIN, HashedPin(hash_hex=KNOWN_ANSWER_HASH_HEX, salt_hex=KNOWN_ANSWER_SALT_HEX)
    )
    assert compared_pairs == [
        (bytes.fromhex(KNOWN_ANSWER_HASH_HEX), bytes.fromhex(KNOWN_ANSWER_HASH_HEX))
    ]


def test_spend_time_of_one_pin_check_runs_exactly_one_scrypt(
    hasher: ScryptPinHasher, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The decoy check costs what a real check costs: one scrypt derivation."""
    derivation_count = 0
    real_scrypt = hashlib.scrypt

    def counting_scrypt(password: bytes, **parameters: int | bytes) -> bytes:
        """Counts each derivation and delegates to the real scrypt."""
        nonlocal derivation_count
        derivation_count += 1
        return real_scrypt(password, **parameters)  # type: ignore[arg-type]

    monkeypatch.setattr("emi_copilot.core.pin_hasher.hashlib.scrypt", counting_scrypt)
    hasher.spend_time_of_one_pin_check(SYNTHETIC_PIN)
    assert derivation_count == 1
