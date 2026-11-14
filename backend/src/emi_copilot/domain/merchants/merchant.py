"""Merchant entity: one shop, its pairing PIN in hashed form and its PIN attempt record."""

import re
from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.merchants.pin_lockout_policy import PinAttemptState
from emi_copilot.domain.payments.field_validation import require_non_empty_text

# Shop codes such as RAVI-0193: upper-case letters, digits and hyphens, as printed for the shop.
SHOP_CODE_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9-]{0,31}")
_LOWERCASE_HEX_PATTERN = re.compile(r"[0-9a-f]+")


@dataclass(frozen=True, slots=True)
class Merchant:
    """A shop that pairs counter devices with a PIN; only the PIN's hash and salt are held.

    The counter device label is the name given to each device paired with this shop's PIN, for
    example "Counter tablet 1". The PIN attempt state drives the lockout policy.
    """

    id: str
    shop_code: str
    display_name: str
    counter_device_label: str
    pin_hash_hex: str
    pin_salt_hex: str
    pin_attempt_state: PinAttemptState

    def __post_init__(self) -> None:
        """Rejects blank names, a malformed shop code and a PIN hash or salt that is not hex."""
        for text, description in (
            (self.id, "merchant id"),
            (self.display_name, "shop name"),
            (self.counter_device_label, "counter device label"),
        ):
            require_non_empty_text(text, description, InvalidMerchantDataError)
        if not isinstance(self.shop_code, str) or not SHOP_CODE_PATTERN.fullmatch(self.shop_code):
            raise InvalidMerchantDataError(
                "The shop code must be 1 to 32 upper-case letters, digits or hyphens."
            )
        for hex_text, description in (
            (self.pin_hash_hex, "PIN hash"),
            (self.pin_salt_hex, "PIN salt"),
        ):
            if not isinstance(hex_text, str) or not _LOWERCASE_HEX_PATTERN.fullmatch(hex_text):
                raise InvalidMerchantDataError(f"The {description} must be lowercase hex.")
