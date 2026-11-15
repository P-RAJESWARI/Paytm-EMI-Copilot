"""NumberToken: one number found in AI text, as the original span and its checked value."""

from dataclasses import dataclass
from enum import StrEnum


class NumberTokenKind(StrEnum):
    """What a found number is, which decides the allowed set it is checked against."""

    RUPEE_AMOUNT = "RUPEE_AMOUNT"
    PLAIN_NUMBER = "PLAIN_NUMBER"
    MALFORMED = "MALFORMED"
    UNCHECKABLE = "UNCHECKABLE"


@dataclass(frozen=True, slots=True)
class NumberToken:
    """A number as written in the text; value is None when it is malformed or uncheckable."""

    text: str
    value: int | None
    kind: NumberTokenKind
