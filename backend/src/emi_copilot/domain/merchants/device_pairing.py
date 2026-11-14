"""DevicePairing entity: one counter device's access, known only by its token's hash."""

import re
from dataclasses import dataclass
from datetime import datetime

from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_timezone_aware_moment,
)

_TOKEN_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class DevicePairing:
    """A paired device: whose it is, its label, its token's SHA-256 and its expiry or revocation.

    The token itself is never held here; it is shown once to the device and then forgotten.
    """

    id: str
    merchant_id: str
    device_label: str
    access_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None

    def __post_init__(self) -> None:
        """Rejects blank ids or label, a malformed token hash and timestamps without a time zone."""
        for text, description in (
            (self.id, "device pairing id"),
            (self.merchant_id, "merchant id"),
            (self.device_label, "device label"),
        ):
            require_non_empty_text(text, description, InvalidMerchantDataError)
        if not isinstance(self.access_token_hash, str) or not _TOKEN_HASH_PATTERN.fullmatch(
            self.access_token_hash
        ):
            raise InvalidMerchantDataError("The access token hash must be 64 lowercase hex digits.")
        require_timezone_aware_moment(self.expires_at, "expiry", InvalidMerchantDataError)
        if self.revoked_at is not None:
            require_timezone_aware_moment(self.revoked_at, "revocation", InvalidMerchantDataError)

    def is_usable_at(self, now: datetime) -> bool:
        """Tells whether the token still signs the device in: not revoked and not yet expired."""
        return self.revoked_at is None and now < self.expires_at
