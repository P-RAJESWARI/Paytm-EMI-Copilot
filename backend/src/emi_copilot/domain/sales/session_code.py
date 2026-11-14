"""SessionCode value object: the 4-digit number that tells sales apart on the counter screen."""

import re
from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidSaleDataError

SESSION_CODE_DIGIT_COUNT = 4
_SESSION_CODE_PATTERN = re.compile(r"[0-9]{4}")


# Pattern: Value Object. A code is always exactly four ASCII digits, leading zeros kept.
@dataclass(frozen=True, slots=True)
class SessionCode:
    """A display label such as "4821", unique among one shop's open sales.

    It is never a credential: the QR token, not this code, links a phone to a sale, so guessing
    a code gives access to nothing.
    """

    value: str

    def __post_init__(self) -> None:
        """Rejects anything but exactly four ASCII digits."""
        if not isinstance(self.value, str) or _SESSION_CODE_PATTERN.fullmatch(self.value) is None:
            raise InvalidSaleDataError("A session code must be exactly four digits.")
