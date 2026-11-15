"""NumberTokenExtractor: digits in any script and grouping, number words, and uncheckable forms."""

import unicodedata

import pytest

from emi_copilot.domain.number_audit import (
    NumberToken,
    NumberTokenExtractor,
    NumberTokenKind,
    number_words,
)
from emi_copilot.domain.number_audit.normalised_text import NormalisedText
from emi_copilot.domain.number_audit.number_token_extractor import is_valid_digit_grouping

RUPEE = NumberTokenKind.RUPEE_AMOUNT
PLAIN = NumberTokenKind.PLAIN_NUMBER
MALFORMED = NumberTokenKind.MALFORMED
UNCHECKABLE = NumberTokenKind.UNCHECKABLE
# Written as escapes because they look like ASCII: fullwidth 3,667, the Tamil zero, and the
# fraction slash that NFKC puts inside the one-half sign.
FULLWIDTH_3667 = "\uff13,\uff16\uff16\uff17"
TAMIL_DIGIT_ZERO = "\u0be6"
FRACTION_SLASH = "\u2044"


def extract(text: str) -> list[tuple[str, int | None, NumberTokenKind]]:
    """Gives each token of a text as (span, value, kind) for compact assertions."""
    return [(token.text, token.value, token.kind) for token in NumberTokenExtractor().extract(text)]


@pytest.mark.parametrize(
    ("text", "expected_tokens"),
    [
        ("₹3,667", [("₹3,667", 3667, RUPEE)]),
        ("₹ 3667", [("₹ 3667", 3667, RUPEE)]),
        ("Rs. 1,84,000", [("Rs. 1,84,000", 184_000, RUPEE)]),
        ("rs 184,000", [("rs 184,000", 184_000, RUPEE)]),
        ("INR184000", [("INR184000", 184_000, RUPEE)]),
        ("2,600 rupees", [("2,600 rupees", 2600, RUPEE)]),
        ("1 rupee", [("1 rupee", 1, RUPEE)]),
        ("2,600 ரூபாய்", [("2,600 ரூபாய்", 2600, RUPEE)]),
        ("2,600 ரூ", [("2,600 ரூ", 2600, RUPEE)]),
        ("₨500", [("₨500", 500, RUPEE)]),
        ("6 months", [("6", 6, PLAIN)]),
        ("a 12-month plan", [("12", 12, PLAIN)]),
        ("₹3,667.00 and ₹0.0", [("₹3,667.00", 3667, RUPEE), ("₹0.0", 0, RUPEE)]),
    ],
)
def test_extractor_digits_with_markers_give_rupee_amounts_and_others_plain_numbers(
    text: str, expected_tokens: list[tuple[str, int | None, NumberTokenKind]]
) -> None:
    """₹, Rs, Rs. and INR prefixes and rupee suffixes mark amounts; spans are kept as written."""
    assert extract(text) == expected_tokens


def test_extractor_tamil_and_fullwidth_digits_read_as_ascii_and_keep_their_spans() -> None:
    """NFKC and Unicode digit values make every script's digits comparable."""
    assert extract(f"₹௩,௬௬௭ / ₹{FULLWIDTH_3667}") == [
        ("₹௩,௬௬௭", 3667, RUPEE),
        (f"₹{FULLWIDTH_3667}", 3667, RUPEE),
    ]


@pytest.mark.parametrize("text", ["3,6,67", "36,67", "1,0000", "1234,567", "123,45,678"])
def test_extractor_comma_pattern_outside_western_and_indian_grouping_is_malformed(
    text: str,
) -> None:
    """Only plain, Western and Indian grouping are trusted."""
    assert extract(f"₹{text}") == [(f"₹{text}", None, MALFORMED)]


@pytest.mark.parametrize(
    ("digits", "expected_valid"),
    [
        ("3667", True),
        ("3,667", True),
        ("1,184,000", True),
        ("11,84,000", True),
        ("1,00,00,000", True),
        ("1234,567", False),
        ("3,6,67", False),
    ],
)
def test_is_valid_digit_grouping_accepts_only_known_groupings(
    digits: str, *, expected_valid: bool
) -> None:
    """Western groups are threes; Indian groups are pairs before a final three."""
    assert is_valid_digit_grouping(digits) is expected_valid


@pytest.mark.parametrize(
    ("text", "expected_span"),
    [
        ("₹3,666.67", "₹3,666.67"),
        ("on the 1st", "1st"),
        ("the 2nd plan", "2nd"),
        ("₹3,667.000", "₹3,667.000"),
    ],
)
def test_extractor_paise_fractions_and_ordinals_are_uncheckable(
    text: str, expected_span: str
) -> None:
    """Whole rupees and counts are all the audit compares; anything finer cannot be checked."""
    assert extract(text) == [(expected_span, None, UNCHECKABLE)]


def test_extractor_percent_sign_is_uncheckable_beside_its_number() -> None:
    """38.9% gives an uncheckable fraction and an uncheckable %."""
    assert extract("38.9%") == [("38.9", None, UNCHECKABLE), ("%", None, UNCHECKABLE)]


@pytest.mark.parametrize(
    ("text", "expected_tokens"),
    [
        ("six months", [("six", 6, PLAIN)]),
        ("Twelve", [("Twelve", 12, PLAIN)]),
        ("sixty", [("sixty", 60, PLAIN)]),
        ("ஆறு மாதங்கள்", [("ஆறு", 6, PLAIN)]),
        ("பன்னிரண்டு", [("பன்னிரண்டு", 12, PLAIN)]),
        ("someone often tone", []),
        ("three thousand", [("three", 3, PLAIN), ("thousand", None, UNCHECKABLE)]),
        ("2 lakhs", [("2", 2, PLAIN), ("lakhs", None, UNCHECKABLE)]),
        ("the first payment", [("first", None, UNCHECKABLE)]),
        ("ten percent", [("ten", 10, PLAIN), ("percent", None, UNCHECKABLE)]),
        ("மூன்று ஆயிரம்", [("மூன்று", 3, PLAIN), ("ஆயிரம்", None, UNCHECKABLE)]),
        ("ஆயிரத்து", [("ஆயிரத்து", None, UNCHECKABLE)]),
        ("இரண்டு லட்சம்", [("இரண்டு", 2, PLAIN), ("லட்சம்", None, UNCHECKABLE)]),
        ("௱", [("௱", None, UNCHECKABLE)]),
    ],
)
def test_extractor_number_words_are_plain_and_magnitude_words_uncheckable(
    text: str, expected_tokens: list[tuple[str, int | None, NumberTokenKind]]
) -> None:
    """Small number words are checked like digits; magnitudes and ordinals cannot be."""
    assert extract(text) == expected_tokens


def test_extractor_gives_tokens_in_reading_order() -> None:
    """Digits, words and signs found by different rules come back in text order."""
    assert [token.text for token in NumberTokenExtractor().extract("six, ₹3,667, 5%, ten")] == [
        "six",
        "₹3,667",
        "5",
        "%",
        "ten",
    ]


def test_extractor_text_without_numbers_gives_no_tokens() -> None:
    """Plain words alone are not numbers."""
    assert NumberTokenExtractor().extract("The extra you pay in total is nothing.") == ()


def test_extractor_same_text_gives_the_same_tokens() -> None:
    """Extraction is deterministic."""
    text = f"₹3,667 for six months, ₹{TAMIL_DIGIT_ZERO} extra"
    assert NumberTokenExtractor().extract(text) == NumberTokenExtractor().extract(text)
    assert NumberTokenExtractor().extract(text)[0] == NumberToken("₹3,667", 3667, RUPEE)


def test_normalised_text_maps_an_expanded_character_back_to_its_original() -> None:
    """NFKC may turn one character into several; each still points at the original one."""
    normalised_text = NormalisedText.from_text("x½y")
    assert normalised_text.searchable_text == f"x1{FRACTION_SLASH}2y"
    assert normalised_text.original_span(1, 4) == "½"


def test_number_word_tables_are_canonically_composed() -> None:
    """Text is matched after NFC, so the Tamil tables must be NFC too, or words would be missed."""
    tamil_words = [*number_words.TAMIL_NUMBER_WORDS, *number_words.TAMIL_UNCHECKABLE_WORD_STEMS]
    for word in tamil_words:
        assert unicodedata.normalize("NFC", word) == word
