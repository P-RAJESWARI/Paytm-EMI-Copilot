"""Signed, expiring customer QR tokens: HMAC-SHA256 over a sale id, a nonce and the expiry.

A token is `<base64url payload>.<base64url signature>`, where the payload is compact JSON of
{"expiresAt": <Unix seconds>, "nonce": ..., "saleId": ...}. Only the SHA-256 of the nonce is
stored on the sale, so a database read cannot be turned back into a working QR code, and a new
token voids the old one by replacing that hash. The token travels in the URL fragment
(`/#t=<token>`), which browsers never send to a server, so it never reaches an access log.
"""

import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from emi_copilot.core.clock import Clock

MINIMUM_SIGNING_KEY_LENGTH_IN_BYTES = 32
MAXIMUM_TOKEN_LENGTH = 512
NONCE_ENTROPY_IN_BYTES = 16
_TOKEN_PATTERN = re.compile(r"([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)")
_CLAIM_KEYS = frozenset({"expiresAt", "nonce", "saleId"})


class QrTokenRejectionReason(StrEnum):
    """Why a QR token was refused; a tampered token and a wrong key look the same."""

    MALFORMED = "MALFORMED"
    SIGNATURE_MISMATCH = "SIGNATURE_MISMATCH"
    EXPIRED = "EXPIRED"


class QrTokenRejectedError(Exception):
    """Raised when a QR token is malformed, not signed by our key, or past its expiry.

    The message names the reason only, never the token. Layer 3 turns it into the calm 401
    "ask the shop for a new QR" answer.
    """

    def __init__(self, reason: QrTokenRejectionReason) -> None:
        """Keeps the reason; the token itself is never part of the error."""
        super().__init__(f"QR token rejected: {reason.value}")
        self.reason = reason


@dataclass(frozen=True, slots=True)
class QrTokenClaims:
    """What a token says: which sale, its one-off nonce and when it stops working (UTC).

    expires_at is whole seconds, because the token carries it as Unix seconds.
    """

    sale_id: str
    nonce: str = field(repr=False)
    expires_at: datetime

    def __post_init__(self) -> None:
        """Rejects blank ids or nonce and an expiry that is naive or not whole seconds."""
        if not self.sale_id or not self.nonce:
            raise ValueError("A QR token needs a sale id and a nonce.")
        if self.expires_at.utcoffset() is None or self.expires_at.microsecond != 0:
            raise ValueError("A QR token expiry must be timezone-aware whole seconds.")


@dataclass(frozen=True, slots=True)
class IssuedQrToken:
    """A new token to show once, the nonce hash to store, and the expiry to display."""

    token: str = field(repr=False)
    nonce_hash: str
    expires_at: datetime


def hash_qr_token_nonce(nonce: str) -> str:
    """Gives the lowercase hex SHA-256 of a nonce, the only form in which it is stored."""
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


def _encode_base64url(raw_bytes: bytes) -> str:
    """Encodes bytes as unpadded base64url text."""
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def _decode_base64url(encoded_text: str) -> bytes:
    """Decodes unpadded base64url text; a malformed part raises the MALFORMED rejection."""
    try:
        return base64.urlsafe_b64decode(encoded_text + "=" * (-len(encoded_text) % 4))
    except (binascii.Error, ValueError) as decoding_error:
        raise QrTokenRejectedError(QrTokenRejectionReason.MALFORMED) from decoding_error


def _parse_claims(payload_bytes: bytes) -> QrTokenClaims:
    """Reads the signed payload; anything but the three expected, well-typed keys is malformed."""
    try:
        payload = json.loads(payload_bytes)
        if not isinstance(payload, dict) or set(payload) != _CLAIM_KEYS:
            raise QrTokenRejectedError(QrTokenRejectionReason.MALFORMED)
        expires_at_in_seconds = payload["expiresAt"]
        if isinstance(expires_at_in_seconds, bool) or not isinstance(expires_at_in_seconds, int):
            raise QrTokenRejectedError(QrTokenRejectionReason.MALFORMED)
        if not isinstance(payload["saleId"], str) or not isinstance(payload["nonce"], str):
            raise QrTokenRejectedError(QrTokenRejectionReason.MALFORMED)
        return QrTokenClaims(
            sale_id=payload["saleId"],
            nonce=payload["nonce"],
            expires_at=datetime.fromtimestamp(expires_at_in_seconds, UTC),
        )
    except (ValueError, OverflowError, OSError) as parsing_error:
        raise QrTokenRejectedError(QrTokenRejectionReason.MALFORMED) from parsing_error


class QrTokenSigner:
    """Issues and verifies customer QR tokens with one HMAC-SHA256 key and the injected clock.

    Verification checks the signature in constant time before it reads any claim, and a token
    is valid only while now < expires_at.
    """

    def __init__(self, signing_key: bytes, clock: Clock) -> None:
        """Keeps a key of at least 32 bytes and the clock that decides expiry."""
        if len(signing_key) < MINIMUM_SIGNING_KEY_LENGTH_IN_BYTES:
            raise ValueError(
                f"A QR signing key needs at least {MINIMUM_SIGNING_KEY_LENGTH_IN_BYTES} bytes."
            )
        self._signing_key = signing_key
        self._clock = clock

    def issue(self, sale_id: str, lifetime: timedelta) -> IssuedQrToken:
        """Draws a 128-bit nonce and signs a token that expires lifetime from now, in whole seconds.

        The expiry is rounded down to the second, so a token never outlives its lifetime.
        """
        nonce = secrets.token_urlsafe(NONCE_ENTROPY_IN_BYTES)
        expires_at = (self._clock.now() + lifetime).astimezone(UTC).replace(microsecond=0)
        token = self.sign(QrTokenClaims(sale_id=sale_id, nonce=nonce, expires_at=expires_at))
        return IssuedQrToken(
            token=token, nonce_hash=hash_qr_token_nonce(nonce), expires_at=expires_at
        )

    def sign(self, claims: QrTokenClaims) -> str:
        """Gives the token for the claims; the same claims and key always give the same token."""
        payload_text = json.dumps(
            {
                "expiresAt": int(claims.expires_at.timestamp()),
                "nonce": claims.nonce,
                "saleId": claims.sale_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        encoded_payload = _encode_base64url(payload_text.encode("utf-8"))
        return f"{encoded_payload}.{self._calculate_signature(encoded_payload)}"

    def verify(self, token: str) -> QrTokenClaims:
        """Gives the claims of a valid token, or raises QrTokenRejectedError with the reason."""
        token_match = (
            _TOKEN_PATTERN.fullmatch(token) if len(token) <= MAXIMUM_TOKEN_LENGTH else None
        )
        if token_match is None:
            raise QrTokenRejectedError(QrTokenRejectionReason.MALFORMED)
        encoded_payload, encoded_signature = token_match.groups()
        # Comparing the canonical text, not decoded bytes, also refuses re-encoded signatures.
        if not hmac.compare_digest(self._calculate_signature(encoded_payload), encoded_signature):
            raise QrTokenRejectedError(QrTokenRejectionReason.SIGNATURE_MISMATCH)
        claims = _parse_claims(_decode_base64url(encoded_payload))
        if self._clock.now() >= claims.expires_at:
            raise QrTokenRejectedError(QrTokenRejectionReason.EXPIRED)
        return claims

    def _calculate_signature(self, encoded_payload: str) -> str:
        """Gives the base64url HMAC-SHA256 of the encoded payload under this signer's key."""
        signature = hmac.new(
            self._signing_key, encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        return _encode_base64url(signature)
