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

ENGLISH_UNCHECKABLE_WORDS = frozenset(
    {
        "hundred", "hundreds", "thousand", "thousands", "lakh", "lakhs", "lac", "lacs",
        "crore", "crores", "million", "millions", "billion", "billions",
        "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth",
        "tenth", "eleventh", "twelfth", "twentieth", "thirtieth",
        "percent", "percentage",
    }
)  # fmt: skip

# Matched as word starts, so inflected forms ("ஆயிரத்து", "லட்சத்தில்") are caught too.
# draft: needs native review
TAMIL_UNCHECKABLE_WORD_STEMS = ("ஆயிர", "லட்ச", "கோடி")

TAMIL_NUMERIC_LETTERS = "௰௱௲"
"""Tamil ten, hundred and thousand signs; they are not decimal digits, so never checkable."""
