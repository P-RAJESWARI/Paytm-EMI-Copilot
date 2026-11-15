"""SpokenAmountParser: turns a speech transcript into one monthly budget amount, or none.

Deterministic and LLM-free: it reuses the number audit's extractor and number words, so "3,000",
"₹3,000", "3 thousand", "three thousand" and "மூன்று ஆயிரம்" all read as ₹3,000. The customer
still confirms the amount on screen; this parser never sets the budget itself.
"""

from emi_copilot.domain.number_audit import NumberToken, NumberTokenExtractor, NumberTokenKind
from emi_copilot.domain.number_audit.number_words import (
    ENGLISH_MAGNITUDE_MULTIPLIERS,
    TAMIL_MAGNITUDE_MULTIPLIERS_BY_STEM,
)

PAISE_PER_RUPEE = 100


def magnitude_multiplier_of(token: NumberToken) -> int | None:
    """Gives the multiplier of a magnitude word ("thousand" is 1,000), or None for other tokens."""
    if token.kind is not NumberTokenKind.UNCHECKABLE:
        return None
    english_multiplier = ENGLISH_MAGNITUDE_MULTIPLIERS.get(token.text.lower())
    if english_multiplier is not None:
        return english_multiplier
    return next(
        (
            multiplier
            for stem, multiplier in TAMIL_MAGNITUDE_MULTIPLIERS_BY_STEM.items()
            if token.text.startswith(stem)
        ),
        None,
    )


def combine_spoken_amounts(tokens: tuple[NumberToken, ...]) -> list[int]:
    """Gives each amount said, joining a number with the magnitude word right after it.

    A magnitude word alone ("a thousand") counts as one of it. Other uncheckable tokens (%,
    ordinals, paise) and malformed numbers are not amounts. "three thousand five hundred" gives
    two amounts, so it is treated as unclear rather than guessed.
    """
    amounts: list[int] = []
    pending_value: int | None = None
    for token in tokens:
        multiplier = magnitude_multiplier_of(token)
        if multiplier is not None:
            amounts.append((1 if pending_value is None else pending_value) * multiplier)
            pending_value = None
        elif token.value is not None:
            if pending_value is not None:
                amounts.append(pending_value)
            pending_value = token.value
    if pending_value is not None:
        amounts.append(pending_value)
    return amounts


class SpokenAmountParser:
    """Reads the one rupee amount in a transcript and flags results the customer should check."""

    def __init__(self) -> None:
        """Builds the shared number extractor."""
        self._extractor = NumberTokenExtractor()

    def parse_amount_in_paise(self, transcript: str) -> int | None:
        """Gives the amount in paise when exactly one distinct amount was said; otherwise None."""
        distinct_amounts = set(combine_spoken_amounts(self._extractor.extract(transcript)))
        if len(distinct_amounts) != 1:
            return None
        return distinct_amounts.pop() * PAISE_PER_RUPEE

    def is_likely_misheard(self, amount_in_paise: int | None, product_price_in_paise: int) -> bool:
        """Tells whether to ask again: no single amount, zero, or more each month than the price."""
        return amount_in_paise is None or not 0 < amount_in_paise <= product_price_in_paise
