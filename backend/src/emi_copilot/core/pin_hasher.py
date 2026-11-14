"""Salted scrypt hashing of merchant pairing PINs, compared in constant time.

A 6-digit PIN has only a million values, so no hash makes a leaked table safe on its own; the
salt stops precomputed tables and the slow hash slows a bulk search. Online guessing is stopped
by the lockout policy and the rate limiter, not by this module.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass

SALT_LENGTH_IN_BYTES = 16
HASH_LENGTH_IN_BYTES = 32
# scrypt cost parameters (RFC 7914): about 16 MiB of memory and tens of milliseconds per hash.
SCRYPT_COST_FACTOR = 2**14
SCRYPT_BLOCK_SIZE = 8
SCRYPT_PARALLELISM = 1


@dataclass(frozen=True, slots=True)
class HashedPin:
    """A PIN's scrypt hash and the random salt it was made with, both as lowercase hex."""

    hash_hex: str
    salt_hex: str


def _derive_pin_hash(pin: str, salt: bytes) -> bytes:
    """Runs scrypt over the PIN's UTF-8 bytes with the given salt and the fixed cost parameters."""
    return hashlib.scrypt(
        pin.encode("utf-8"),
        salt=salt,
        n=SCRYPT_COST_FACTOR,
        r=SCRYPT_BLOCK_SIZE,
        p=SCRYPT_PARALLELISM,
        dklen=HASH_LENGTH_IN_BYTES,
    )


class ScryptPinHasher:
    """Hashes new PINs with a fresh salt and checks a PIN against a stored hash.

    It also keeps one hash of a random value, so a pairing request for an unknown shop can spend
    the same time as a wrong PIN for a known one and the two cannot be told apart.
    """

    def __init__(self) -> None:
        """Prepares the decoy hash once, so each decoy check costs exactly one scrypt run."""
        self._decoy_pin = self.hash_new_pin(secrets.token_hex(SALT_LENGTH_IN_BYTES))

    def hash_new_pin(self, pin: str) -> HashedPin:
        """Hashes a PIN with a new random salt, ready to be stored."""
        salt = secrets.token_bytes(SALT_LENGTH_IN_BYTES)
        return HashedPin(hash_hex=_derive_pin_hash(pin, salt).hex(), salt_hex=salt.hex())

    def is_matching_pin(self, pin: str, stored_pin: HashedPin) -> bool:
        """Tells whether the PIN hashes to the stored hash; the comparison is constant time."""
        candidate_hash = _derive_pin_hash(pin, bytes.fromhex(stored_pin.salt_hex))
        return hmac.compare_digest(candidate_hash, bytes.fromhex(stored_pin.hash_hex))

    def spend_time_of_one_pin_check(self, pin: str) -> None:
        """Checks the PIN against the decoy hash and discards the answer, to equalise timing."""
        self.is_matching_pin(pin, self._decoy_pin)
