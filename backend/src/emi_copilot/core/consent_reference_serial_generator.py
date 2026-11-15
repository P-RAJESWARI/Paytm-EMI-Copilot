"""Injectable source of the four-digit serial in a consent reference (EMI-DDMM-NNNN)."""

import secrets
from typing import Protocol

CONSENT_REFERENCE_SERIAL_COUNT = 10_000
"""Every serial from 0000 to 9999."""


class ConsentReferenceSerialGenerator(Protocol):
    """Anything that can give a serial number from 0 to 9999 for a new consent reference."""

    def new_serial_number(self) -> int:
        """Returns a serial number from 0 to 9999."""
        ...


class RandomConsentReferenceSerialGenerator:
    """Draws serials from the operating system, so a reference reveals no count of consents.

    A reference is a display label, not an identifier (the consent id is), so two consents may
    share one; tests inject a fixed generator instead.
    """

    def new_serial_number(self) -> int:
        """Returns a uniformly random serial number from 0 to 9999."""
        return secrets.randbelow(CONSENT_REFERENCE_SERIAL_COUNT)
