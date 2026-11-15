"""Number words the audit reads as plain numbers, and words that make a number uncheckable.

A number word is checked like digits. Magnitude words ("three thousand"), ordinals and Tamil
numeric letters cannot be checked against whole engine figures, so they always fail the audit and
the template text is shown instead (plan Q4). Lists are in lower case.
"""

from types import MappingProxyType

ENGLISH_NUMBER_WORDS = MappingProxyType(
    {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
        "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
        "fifty": 50, "sixty": 60,
    }
)  # fmt: skip

# draft: needs native review (every Tamil number word)
TAMIL_NUMBER_WORDS = MappingProxyType(
    {
        "ஒன்று": 1, "இரண்டு": 2, "மூன்று": 3, "நான்கு": 4, "ஐந்து": 5, "ஆறு": 6,
        "ஏழு": 7, "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10, "பதினொன்று": 11, "பன்னிரண்டு": 12,
    }
)  # fmt: skip

ENGLISH_MAGNITUDE_MULTIPLIERS = MappingProxyType(
    {
        "hundred": 100, "hundreds": 100, "thousand": 1_000, "thousands": 1_000,
        "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
        "million": 1_000_000, "millions": 1_000_000, "crore": 10_000_000,
        "crores": 10_000_000, "billion": 1_000_000_000, "billions": 1_000_000_000,
    }
)  # fmt: skip
"""Magnitude words: uncheckable in AI text, but the spoken budget parser multiplies by them."""

ENGLISH_UNCHECKABLE_WORDS = frozenset(
    {
        *ENGLISH_MAGNITUDE_MULTIPLIERS,
        "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth",
        "tenth", "eleventh", "twelfth", "twentieth", "thirtieth",
        "percent", "percentage",
    }
)  # fmt: skip

# Matched as word starts, so inflected forms ("ஆயிரத்து", "லட்சத்தில்") are caught too.
# draft: needs native review
TAMIL_MAGNITUDE_MULTIPLIERS_BY_STEM = MappingProxyType(
    {"ஆயிர": 1_000, "லட்ச": 100_000, "கோடி": 10_000_000}
)
TAMIL_UNCHECKABLE_WORD_STEMS = tuple(TAMIL_MAGNITUDE_MULTIPLIERS_BY_STEM)

TAMIL_NUMERIC_LETTERS = "௰௱௲"
"""Tamil ten, hundred and thousand signs; they are not decimal digits, so never checkable."""
