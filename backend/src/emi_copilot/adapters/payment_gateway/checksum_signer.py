"""Paytm checksum signing and verification, ported from the official algorithm (ADR 0003).

Source of the algorithm: the official Python library paytmchecksum 1.7.0
(github.com/paytm/Paytm_Python_Checksum, PaytmChecksum.py), as described on paytmpayments.com/docs
/checksum and /docs/checksum-implementation [Verify]. The signature of a text is
base64(AES-CBC(key, fixed iv, PKCS#7 pad(sha256_hex(text + "|" + salt) + salt))), with a salt of
four random characters. A mapping signs as the values of its sorted keys joined by "|", where a
"null" value (any case) signs as empty text. This port uses `cryptography`, takes the salt from
an injectable source and compares in constant time.
"""

import base64
import hashlib
import hmac
import secrets
from collections.abc import Mapping
from typing import Protocol

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pydantic import SecretStr

from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    CHECKSUM_ACCEPTED_KEY_LENGTHS_IN_BYTES,
    CHECKSUM_FIELD_SEPARATOR,
    CHECKSUM_INITIALISATION_VECTOR,
    CHECKSUM_NULL_TEXT,
    CHECKSUM_SALT_ALPHABET,
    CHECKSUM_SALT_LENGTH,
    WEBHOOK_CHECKSUM_FIELD,
)

AES_BLOCK_SIZE_IN_BITS = 128


class ChecksumSaltSource(Protocol):
    """Anything that gives a fresh checksum salt; tests inject a fixed one."""

    def new_salt(self) -> str:
        """Returns four characters from [A-Za-z0-9]."""
        ...


class SecureRandomSaltSource:
    """Draws each salt character with the `secrets` module, as unpredictable as the OS allows."""

    def new_salt(self) -> str:
        """Returns four characters drawn uniformly from [A-Za-z0-9]."""
        return "".join(secrets.choice(CHECKSUM_SALT_ALPHABET) for _ in range(CHECKSUM_SALT_LENGTH))


def build_signed_text_for_fields(fields: Mapping[str, str]) -> str:
    """Gives the text a mapping signs as: values of the sorted keys joined by "|", "null" as ""."""
    return CHECKSUM_FIELD_SEPARATOR.join(
        "" if fields[field_name].lower() == CHECKSUM_NULL_TEXT else fields[field_name]
        for field_name in sorted(fields)
    )


def calculate_salted_hash(text: str, salt: str) -> str:
    """Gives sha256_hex("text|salt") followed by the salt: the text that is then encrypted."""
    salted_text = f"{text}{CHECKSUM_FIELD_SEPARATOR}{salt}"
    return hashlib.sha256(salted_text.encode("utf-8")).hexdigest() + salt


def _require_valid_salt(salt: str) -> None:
    """Raises unless the salt is exactly four characters from [A-Za-z0-9]."""
    if len(salt) != CHECKSUM_SALT_LENGTH or not set(salt) <= set(CHECKSUM_SALT_ALPHABET):
        raise ValueError("A checksum salt must be four characters from [A-Za-z0-9].")


class PaytmChecksumSigner:
    """Signs request text and verifies received signatures with the merchant key.

    It keeps the vendor's signing scheme out of the adapter, and a pinned salt source gives
    tests a known-answer vector. The key is held as a SecretStr and never appears in a repr, log
    line or error message. Verification never raises for a malformed signature; it answers False.
    """

    def __init__(
        self, merchant_key: SecretStr, salt_source: ChecksumSaltSource | None = None
    ) -> None:
        """Keeps the merchant key and the salt source; refuses a key AES cannot use."""
        if len(merchant_key.get_secret_value().encode("utf-8")) not in (
            CHECKSUM_ACCEPTED_KEY_LENGTHS_IN_BYTES
        ):
            raise ValueError("The merchant key must be 16, 24 or 32 bytes long.")
        self._merchant_key = merchant_key
        self._salt_source = salt_source or SecureRandomSaltSource()

    def __repr__(self) -> str:
        """Shows the class only, never the merchant key."""
        return "PaytmChecksumSigner(merchant_key=SecretStr('**********'))"

    def generate_signature_for_text(self, text: str) -> str:
        """Signs an exact text, such as the JSON body bytes that are about to be sent."""
        salt = self._salt_source.new_salt()
        _require_valid_salt(salt)
        return self._encrypt(calculate_salted_hash(text, salt))

    def generate_signature_for_fields(self, fields: Mapping[str, str]) -> str:
        """Signs key/value fields the way the official library signs a dict."""
        return self.generate_signature_for_text(build_signed_text_for_fields(fields))

    def is_signature_valid_for_text(self, text: str, signature: str) -> bool:
        """Tells whether the signature was made with our key over exactly this text."""
        decrypted_hash = self._decrypt_or_none(signature)
        if decrypted_hash is None:
            return False
        expected_hash = calculate_salted_hash(text, decrypted_hash[-CHECKSUM_SALT_LENGTH:])
        return hmac.compare_digest(decrypted_hash.encode("utf-8"), expected_hash.encode("utf-8"))

    def is_signature_valid_for_fields(self, fields: Mapping[str, str], signature: str) -> bool:
        """Tells whether the signature matches every field except CHECKSUMHASH; input unchanged."""
        signed_fields = {
            field_name: field_value
            for field_name, field_value in fields.items()
            if field_name != WEBHOOK_CHECKSUM_FIELD
        }
        return self.is_signature_valid_for_text(
            build_signed_text_for_fields(signed_fields), signature
        )

    def _build_cipher(self) -> Cipher[modes.CBC]:
        """Builds the AES-CBC cipher on the merchant key and the fixed initialisation vector."""
        key_bytes = self._merchant_key.get_secret_value().encode("utf-8")
        return Cipher(algorithms.AES(key_bytes), modes.CBC(CHECKSUM_INITIALISATION_VECTOR))

    def _encrypt(self, salted_hash: str) -> str:
        """Pads, encrypts and base64-encodes the salted hash."""
        padder = padding.PKCS7(AES_BLOCK_SIZE_IN_BITS).padder()
        padded_bytes = padder.update(salted_hash.encode("utf-8")) + padder.finalize()
        encryptor = self._build_cipher().encryptor()
        encrypted_bytes = encryptor.update(padded_bytes) + encryptor.finalize()
        return base64.b64encode(encrypted_bytes).decode("ascii")

    def _decrypt_or_none(self, signature: str) -> str | None:
        """Decodes and decrypts a signature; gives None for bad base64, length, padding or text."""
        try:
            encrypted_bytes = base64.b64decode(signature, validate=True)
            decryptor = self._build_cipher().decryptor()
            padded_bytes = decryptor.update(encrypted_bytes) + decryptor.finalize()
            unpadder = padding.PKCS7(AES_BLOCK_SIZE_IN_BITS).unpadder()
            return (unpadder.update(padded_bytes) + unpadder.finalize()).decode("ascii")
        except ValueError:
            return None
