"""KeyedHasher: HMAC-SHA256 digests of customer values that must be compared, never stored plain.

The customer's phone number is stored only as this digest (plus its last two digits), and a
consent one-time code only as a digest bound to its challenge (security-and-compliance.md
section 2). A secret key stops anyone with the table from simply trying every phone number or
every six-digit code. Each kind of value is hashed under its own purpose label, so a phone
digest can never equal a code digest even under one key.
"""

import hashlib
import hmac

MINIMUM_HASH_KEY_LENGTH_IN_BYTES = 32
_PHONE_NUMBER_PURPOSE = "customer-phone-number"
_CONSENT_OTP_CODE_PURPOSE = "consent-otp-code"
# Separates the purpose and the parts; ids, digits and labels never contain a NUL character.
_PART_SEPARATOR = "\x00"


class KeyedHasher:
    """Hashes customer values with one secret key; equal inputs give equal lowercase hex digests."""

    def __init__(self, key: bytes) -> None:
        """Keeps the key, which must be at least 32 bytes; the key itself is never logged."""
        if len(key) < MINIMUM_HASH_KEY_LENGTH_IN_BYTES:
            raise ValueError(
                f"A hash key must be at least {MINIMUM_HASH_KEY_LENGTH_IN_BYTES} bytes."
            )
        self._key = key

    def hash_customer_phone_number(self, national_number: str) -> str:
        """Gives the stable digest of a ten-digit phone number, for velocity checks and evidence."""
        return self._digest(_PHONE_NUMBER_PURPOSE, national_number)

    def hash_consent_otp_code(self, otp_challenge_id: str, code: str) -> str:
        """Gives the digest of a code for one challenge, so equal codes differ across challenges."""
        return self._digest(_CONSENT_OTP_CODE_PURPOSE, otp_challenge_id, code)

    def _digest(self, purpose: str, *parts: str) -> str:
        """Gives HMAC-SHA256 over the purpose label and the parts, joined unambiguously."""
        message = _PART_SEPARATOR.join((purpose, *parts)).encode("utf-8")
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def __repr__(self) -> str:
        """Names the class only, so the key can never reach a log through repr."""
        return "KeyedHasher(key=<hidden>)"
