"""SpokenAmountParser: one spoken amount becomes paise; anything unclear asks the customer again."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.core.indian_rupee_formatter import group_digits_the_indian_way
from emi_copilot.domain.speech import SpokenAmountParser

THREE_THOUSAND_RUPEES_IN_PAISE = 300_000
PHONE_PRICE_IN_PAISE = 2_200_000
# Written as an escape because it looks like the letter o.
TAMIL_DIGIT_ZERO = "\u0be6"


@pytest.mark.parametrize(
    "transcript",
    [
        "3,000",
        "3000",
        "₹3,000 a month",
        "Rs. 3000",
        "3000 rupees",
        "3 thousand",
        "three thousand",
        "Three Thousand rupees",
        "மூன்று ஆயிரம்",
        "மாதம் ₹3,000",
        f"₹௩,{TAMIL_DIGIT_ZERO * 3}",
        "3,000, yes 3,000",
    ],
)
def test_spoken_amount_parser_one_amount_in_any_form_gives_its_paise(transcript: str) -> None:
    """Digits, grouping, rupee markers, number words and magnitude words all read as ₹3,000."""
    assert SpokenAmountParser().parse_amount_in_paise(transcript) == THREE_THOUSAND_RUPEES_IN_PAISE


@pytest.mark.parametrize(
    ("transcript", "expected_paise"),
    [
        ("a thousand", 100_000),
        ("2 lakh", 20_000_000),
        ("இரண்டு லட்சம்", 20_000_000),
        ("five hundred", 50_000),
        ("₹3,000 a month on the 1st", THREE_THOUSAND_RUPEES_IN_PAISE),
    ],
)
def test_spoken_amount_parser_magnitudes_multiply_and_other_signs_are_ignored(
    transcript: str, expected_paise: int
) -> None:
    """A lone magnitude counts once; ordinals and % are not amounts."""
    assert SpokenAmountParser().parse_amount_in_paise(transcript) == expected_paise


@pytest.mark.parametrize(
    "transcript",
    ["", "I am not sure", "3000 or 4000", "three thousand five hundred", "₹3,000 for 6 months"],
)
def test_spoken_amount_parser_no_amount_or_several_amounts_gives_none(transcript: str) -> None:
    """Unclear speech is never guessed; the customer types or says it again."""
    assert SpokenAmountParser().parse_amount_in_paise(transcript) is None


@given(rupees=st.integers(min_value=1, max_value=10_000_000))
def test_spoken_amount_parser_any_indian_grouped_amount_reads_exactly(rupees: int) -> None:
    """Every amount written with ₹ and Indian grouping reads back to the same paise."""
    transcript = f"₹{group_digits_the_indian_way(rupees)} a month"
    assert SpokenAmountParser().parse_amount_in_paise(transcript) == rupees * 100


@pytest.mark.parametrize(
    ("amount_in_paise", "expected_misheard"),
    [
        (None, True),
        (0, True),
        (THREE_THOUSAND_RUPEES_IN_PAISE, False),
        (PHONE_PRICE_IN_PAISE, False),
        (3_000_000, True),
    ],
)
def test_spoken_amount_parser_is_likely_misheard_flags_missing_zero_and_above_price(
    amount_in_paise: int | None, *, expected_misheard: bool
) -> None:
    """₹30,000 a month for a ₹22,000 phone is the design's misheard example."""
    parser = SpokenAmountParser()
    assert parser.is_likely_misheard(amount_in_paise, PHONE_PRICE_IN_PAISE) is expected_misheard
