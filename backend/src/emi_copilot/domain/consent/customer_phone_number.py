"""CustomerPhoneNumber value object: an Indian mobile number that lives only in memory."""

import re
from dataclasses import dataclass, field

from emi_copilot.domain.errors import InvalidConsentDataError

# Ten digits starting 6 to 9, optionally after the +91 country code (the national plan's mobiles).
_INDIAN_MOBILE_NUMBER_PATTERN = re.compile(r"(?:\+91)?([6-9][0-9]{9})")
_LAST_DIGITS_SHOWN = 2


# Pattern: Value Object. The plain number exists only in memory, to send the one-time code; only
# its last two digits and a keyed hash are stored (security-and-compliance.md section 2).
@dataclass(frozen=True, slots=True)
class CustomerPhoneNumber:
    """An Indian mobile number in national form (ten digits); its repr hides all but two digits.

    Never log it or put it in an error detail, an audit event or a stored record.
    """

    national_number: str = field(repr=False)

    def __post_init__(self) -> None:
        """Normalises +91 numbers to ten digits; anything else not an Indian mobile is rejected."""
        if not isinstance(self.national_number, str):
            raise InvalidConsentDataError("A phone number must be text.")
        number_match = _INDIAN_MOBILE_NUMBER_PATTERN.fullmatch(self.national_number)
        if number_match is None:
            raise InvalidConsentDataError("The phone number is not an Indian mobile number.")
        object.__setattr__(self, "national_number", number_match.group(1))

    @property
    def last_two_digits(self) -> str:
        """Gives the last two digits, the only part ever shown or stored ("ending 42")."""
        return self.national_number[-_LAST_DIGITS_SHOWN:]

    def __repr__(self) -> str:
        """Shows only the last two digits, so a stray log line cannot leak the number."""
        return f"CustomerPhoneNumber(ending {self.last_two_digits})"
