"""SpokenAmountParser: turns a speech transcript into one monthly budget amount, or none.

Deterministic and LLM-free: it reuses the number audit's extractor and number words, so "3,000",
"₹3,000", "3 thousand", "three thousand" and "மூன்று ஆயிரம்" all read as ₹3,000. Sarvam
speech-to-text writes amounts as English words (verified 2026-11-15: "three thousand six hundred
and sixty seven rupees"), so English compound number words are composed into one amount. Tamil
compounds use other stems (for example அறுநூற்று, 600) and are not composed yet: a Tamil number
word followed by a magnitude still reads, a longer Tamil compound reads as several amounts and
the customer is asked again. The customer always confirms the amount on screen.
"""

import re
from dataclasses import dataclass, field

from emi_copilot.domain.number_audit import NumberToken, NumberTokenExtractor, NumberTokenKind
from emi_copilot.domain.number_audit.number_words import (
    ENGLISH_MAGNITUDE_MULTIPLIERS,
    ENGLISH_NUMBER_WORDS,
    TAMIL_MAGNITUDE_MULTIPLIERS_BY_STEM,
    TAMIL_NUMBER_WORDS,
)

PAISE_PER_RUPEE = 100
HUNDRED = 100
TEN = 10
SMALLEST_TENS_WORD = 20
_NUMBER_WORD_ALTERNATIVES = "|".join(
    sorted([*ENGLISH_NUMBER_WORDS, *TAMIL_NUMBER_WORDS], key=len, reverse=True)
)
# A tenure such as "for six months", "12 months" or "ஆறு மாதங்களுக்கு": the months to pay
# over, never the monthly amount. "a month" and "monthly" are not tenures.
TENURE_PHRASE_PATTERN = re.compile(
    rf"(?<![\w,.])(?:[0-9]+|{_NUMBER_WORD_ALTERNATIVES})(?:[\s-]+(?:{_NUMBER_WORD_ALTERNATIVES}))*"
    r"\s*(?:months?(?!\w)|மாத\w*)",
    re.IGNORECASE,
)


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


def is_number_word(token: NumberToken) -> bool:
    """Tells whether a number was written as a word ("sixty"), not with digits ("60")."""
    return token.text.lower() in ENGLISH_NUMBER_WORDS or token.text in TAMIL_NUMBER_WORDS


def can_add_word_to_part(part: int, word_value: int) -> bool:
    """Tells whether a word continues a part: "six hundred" + "sixty", or "sixty" + "seven"."""
    below_hundred = part % HUNDRED
    if below_hundred == 0:
        return part >= HUNDRED and word_value < HUNDRED
    return below_hundred >= SMALLEST_TENS_WORD and part % TEN == 0 and word_value < TEN


@dataclass
class SpokenAmountComposer:
    """Builds amounts from tokens in reading order: "one lakh twenty thousand" is 1,20,000.

    A larger magnitude closes into the total; a magnitude not smaller than the last one starts
    a new amount, so "three thousand or four thousand" stays two amounts. Digits never add to
    an earlier number ("3000 or 4000" is two amounts); they only take a magnitude after them.
    """

    amounts: list[int] = field(default_factory=list)
    total: int = 0
    part: int | None = None
    is_part_a_word: bool = False
    last_large_multiplier: int | None = None

    def add_magnitude(self, multiplier: int) -> None:
        """Multiplies the part by a hundred, or closes it into the total at a larger magnitude."""
        if multiplier == HUNDRED:
            if self.part is not None and self.part >= HUNDRED:
                # "three hundred four hundred": the 4 belongs to the second amount.
                carried = self.part % HUNDRED
                self.part -= carried
                self.finish_amount()
                self.part = carried or None
            self.part = (self.part or 1) * HUNDRED
            self.is_part_a_word = True
            return
        if self.last_large_multiplier is not None and multiplier >= self.last_large_multiplier:
            part = self.part
            self.part = None
            self.finish_amount()
            self.part = part
        self.total += (self.part or 1) * multiplier
        self.last_large_multiplier = multiplier
        self.part = None

    def add_number(self, value: int, *, is_word: bool) -> None:
        """Continues the amount with a number word where English allows it, else starts anew."""
        if self.part is None and (is_word or self.last_large_multiplier is None):
            self.part, self.is_part_a_word = value, is_word
            return
        if (
            self.part is not None
            and is_word
            and self.is_part_a_word
            and can_add_word_to_part(self.part, value)
        ):
            self.part += value
            return
        self.finish_amount()
        self.part, self.is_part_a_word = value, is_word

    def finish_amount(self) -> None:
        """Records the amount built so far, if any, and starts an empty one."""
        if self.part is not None or self.last_large_multiplier is not None:
            self.amounts.append(self.total + (self.part or 0))
        self.total, self.part, self.is_part_a_word = 0, None, False
        self.last_large_multiplier = None


def combine_spoken_amounts(tokens: tuple[NumberToken, ...]) -> list[int]:
    """Gives each amount said, composing number words and magnitudes into whole amounts.

    "three thousand six hundred and sixty seven" is 3,667 and "3 thousand" is 3,000. A
    magnitude word alone ("a thousand") counts as one of it. Other uncheckable tokens (%,
    ordinals, paise) and malformed numbers are not amounts.
    """
    composer = SpokenAmountComposer()
    for token in tokens:
        multiplier = magnitude_multiplier_of(token)
        if multiplier is not None:
            composer.add_magnitude(multiplier)
        elif token.value is not None:
            composer.add_number(token.value, is_word=is_number_word(token))
    composer.finish_amount()
    return composer.amounts


def read_spoken_numbers(extractor: NumberTokenExtractor, text: str) -> list[int]:
    """Gives the amounts said outside tenure phrases, then each tenure's number of months.

    Reading a tenure on its own keeps "three thousand for six months" as 3,000 and 6, never
    3,006 (teach-back scores the monthly amount and the months separately).
    """
    tenure_numbers = [
        number
        for tenure_phrase in TENURE_PHRASE_PATTERN.finditer(text)
        for number in combine_spoken_amounts(extractor.extract(tenure_phrase.group()))
    ]
    amounts = combine_spoken_amounts(extractor.extract(TENURE_PHRASE_PATTERN.sub(" ", text)))
    return [*amounts, *tenure_numbers]


class SpokenAmountParser:
    """Reads the one rupee amount in a transcript and flags results the customer should check."""

    def __init__(self) -> None:
        """Builds the shared number extractor."""
        self._extractor = NumberTokenExtractor()

    def parse_amount_in_paise(self, transcript: str) -> int | None:
        """Gives the amount in paise when exactly one distinct amount was said; otherwise None.

        A tenure ("for six months") is the months to pay over, not an amount, so it is left out.
        """
        without_tenure = TENURE_PHRASE_PATTERN.sub(" ", transcript)
        distinct_amounts = set(combine_spoken_amounts(self._extractor.extract(without_tenure)))
        if len(distinct_amounts) != 1:
            return None
        return distinct_amounts.pop() * PAISE_PER_RUPEE

    def is_likely_misheard(self, amount_in_paise: int | None, product_price_in_paise: int) -> bool:
        """Tells whether to ask again: no single amount, zero, or more each month than the price."""
        return amount_in_paise is None or not 0 < amount_in_paise <= product_price_in_paise
