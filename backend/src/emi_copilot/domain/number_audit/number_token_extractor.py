"""NumberTokenExtractor: finds every number in AI text, written with digits or as a word.

Digits are read after NormalisedText made them ASCII, so ₹௩,௬௬௭ reads as ₹3,667. Plain (3667),
Western (1,184,000) and Indian (11,84,000) grouping give the same value; any other comma pattern
is MALFORMED. A .0 or .00 fraction is the whole number; any other fraction, an ordinal, a % sign,
a magnitude word and a Tamil numeric letter are UNCHECKABLE, because the audit compares whole
rupees and whole counts only (ADR 0001).
"""

import re
from collections.abc import Iterator

from emi_copilot.domain.number_audit.normalised_text import NormalisedText
from emi_copilot.domain.number_audit.number_token import NumberToken, NumberTokenKind
from emi_copilot.domain.number_audit.number_words import (
    ENGLISH_NUMBER_WORDS,
    ENGLISH_UNCHECKABLE_WORDS,
    TAMIL_NUMBER_WORDS,
    TAMIL_NUMERIC_LETTERS,
    TAMIL_UNCHECKABLE_WORD_STEMS,
)

_TAMIL_LETTERS = "஀-௿"
_NOT_AFTER_TAMIL_LETTER = rf"(?<![{_TAMIL_LETTERS}])"
WHOLE_NUMBER_FRACTIONS = frozenset({"0", "00"})
THOUSANDS_GROUP_SIZE = 3
INDIAN_PAIR_GROUP_SIZE = 2

DIGIT_NUMBER_PATTERN = re.compile(
    r"(?P<rupee_prefix>(?:₹|(?<![a-z])rs\.?|(?<![a-z])inr)\s*)?"
    r"(?<![0-9])(?P<digits>[0-9]+(?:,[0-9]+)*)"
    r"(?:\.(?P<fraction>[0-9]+))?"
    r"(?:(?P<ordinal>st|nd|rd|th)(?![a-z])"
    r"|(?P<rupee_suffix>\s*(?:rupees?(?![a-z])|ரூபாய்|ரூ)))?",
    re.IGNORECASE,
)
ENGLISH_WORD_PATTERN = re.compile(r"(?<![a-z0-9])[a-z]+(?![a-z0-9])", re.IGNORECASE)
TAMIL_NUMBER_WORD_PATTERN = re.compile(
    _NOT_AFTER_TAMIL_LETTER
    + "("
    + "|".join(sorted(TAMIL_NUMBER_WORDS, key=len, reverse=True))
    + rf")(?![{_TAMIL_LETTERS}])"
)
UNCHECKABLE_SIGN_PATTERN = re.compile(
    _NOT_AFTER_TAMIL_LETTER
    + "(?:"
    + "|".join(TAMIL_UNCHECKABLE_WORD_STEMS)
    + rf")[{_TAMIL_LETTERS}]*|%|[{TAMIL_NUMERIC_LETTERS}]"
)


def is_valid_digit_grouping(digits: str) -> bool:
    """Accepts no commas, Western groups of three, or Indian pairs before a final three."""
    groups = digits.split(",")
    if len(groups) == 1:
        return True
    first_group, other_groups = groups[0], groups[1:]
    is_western = len(first_group) <= THOUSANDS_GROUP_SIZE and all(
        len(group) == THOUSANDS_GROUP_SIZE for group in other_groups
    )
    is_indian = (
        len(first_group) <= INDIAN_PAIR_GROUP_SIZE
        and len(groups[-1]) == THOUSANDS_GROUP_SIZE
        and all(len(group) == INDIAN_PAIR_GROUP_SIZE for group in groups[1:-1])
    )
    return is_western or is_indian


def classify_digit_number(match: re.Match[str]) -> tuple[NumberTokenKind, int | None]:
    """Gives the kind and whole value of one digit match; None for malformed or uncheckable."""
    digits = match["digits"]
    if not is_valid_digit_grouping(digits):
        return NumberTokenKind.MALFORMED, None
    fraction = match["fraction"]
    if match["ordinal"] or (fraction is not None and fraction not in WHOLE_NUMBER_FRACTIONS):
        return NumberTokenKind.UNCHECKABLE, None
    value = int(digits.replace(",", ""))
    if match["rupee_prefix"] or match["rupee_suffix"]:
        return NumberTokenKind.RUPEE_AMOUNT, value
    return NumberTokenKind.PLAIN_NUMBER, value


class NumberTokenExtractor:
    """Lists the numbers of a text in reading order, each with its original span and kind."""

    def extract(self, text: str) -> tuple[NumberToken, ...]:
        """Finds digits, number words and uncheckable signs; deterministic for the same text."""
        normalised_text = NormalisedText.from_text(text)
        positioned_tokens = sorted(
            [
                *self._find_digit_numbers(normalised_text),
                *self._find_number_words(normalised_text),
                *self._find_uncheckable_signs(normalised_text),
            ],
            key=lambda positioned_token: positioned_token[0],
        )
        return tuple(token for _, token in positioned_tokens)

    def _find_digit_numbers(
        self, normalised_text: NormalisedText
    ) -> Iterator[tuple[int, NumberToken]]:
        """Yields every number written with digits, with its rupee marker or suffix if any."""
        for match in DIGIT_NUMBER_PATTERN.finditer(normalised_text.searchable_text):
            kind, value = classify_digit_number(match)
            span = normalised_text.original_span(match.start(), match.end())
            yield match.start(), NumberToken(span, value, kind)

    def _find_number_words(
        self, normalised_text: NormalisedText
    ) -> Iterator[tuple[int, NumberToken]]:
        """Yields English and Tamil number words as plain numbers, and English uncheckables."""
        searchable_text = normalised_text.searchable_text
        for match in ENGLISH_WORD_PATTERN.finditer(searchable_text):
            word = match.group().lower()
            span = normalised_text.original_span(match.start(), match.end())
            if word in ENGLISH_NUMBER_WORDS:
                plain = NumberToken(span, ENGLISH_NUMBER_WORDS[word], NumberTokenKind.PLAIN_NUMBER)
                yield match.start(), plain
            elif word in ENGLISH_UNCHECKABLE_WORDS:
                yield match.start(), NumberToken(span, None, NumberTokenKind.UNCHECKABLE)
        for match in TAMIL_NUMBER_WORD_PATTERN.finditer(searchable_text):
            span = normalised_text.original_span(match.start(), match.end())
            value = TAMIL_NUMBER_WORDS[match.group()]
            yield match.start(), NumberToken(span, value, NumberTokenKind.PLAIN_NUMBER)

    def _find_uncheckable_signs(
        self, normalised_text: NormalisedText
    ) -> Iterator[tuple[int, NumberToken]]:
        """Yields % signs, Tamil magnitude words and Tamil numeric letters as uncheckable."""
        for match in UNCHECKABLE_SIGN_PATTERN.finditer(normalised_text.searchable_text):
            span = normalised_text.original_span(match.start(), match.end())
            yield match.start(), NumberToken(span, None, NumberTokenKind.UNCHECKABLE)
