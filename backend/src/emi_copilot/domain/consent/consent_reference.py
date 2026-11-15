"""ConsentReference value object: the receipt reference the customer is shown, EMI-DDMM-NNNN."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Self

from emi_copilot.domain.errors import InvalidConsentDataError

_CONSENT_REFERENCE_PATTERN = re.compile(r"EMI-(0[1-9]|[12][0-9]|3[01])(0[1-9]|1[0-2])-[0-9]{4}")
SERIAL_NUMBER_COUNT = 10_000
"""Every serial number from 0000 to 9999."""


# Pattern: Value Object. A display reference like the design's EMI-2611-0042; the consent id, not
# this reference, identifies a record, so two days a year apart may share one.
@dataclass(frozen=True, slots=True)
class ConsentReference:
    """EMI-, the consent day and month (DDMM), and a four-digit serial number."""

    value: str

    def __post_init__(self) -> None:
        """Rejects anything not shaped EMI-DDMM-NNNN with a real day and month number."""
        if (
            not isinstance(self.value, str)
            or _CONSENT_REFERENCE_PATTERN.fullmatch(self.value) is None
        ):
            raise InvalidConsentDataError("A consent reference is shaped EMI-DDMM-NNNN.")

    @classmethod
    def for_consent_day(cls, consent_day: date, serial_number: int) -> Self:
        """Builds the reference for a consent on the shop's calendar day with a serial number."""
        if (
            isinstance(serial_number, bool)
            or not isinstance(serial_number, int)
            or not 0 <= serial_number < SERIAL_NUMBER_COUNT
        ):
            raise InvalidConsentDataError("A consent serial number is from 0 to 9999.")
        return cls(f"EMI-{consent_day:%d%m}-{serial_number:04d}")
