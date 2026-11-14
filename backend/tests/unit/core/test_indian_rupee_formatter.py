"""The weekly message's one money formatter: whole rupees, half-up, Indian digit grouping."""

import pytest

from emi_copilot.core.indian_rupee_formatter import (
    format_paise_as_whole_rupees,
    group_digits_the_indian_way,
)


@pytest.mark.parametrize(
    ("amount_in_paise", "expected_text"),
    [
        (0, "₹0"),
        (49, "₹0"),
        (50, "₹1"),
        (366_667, "₹3,667"),
        (244_444, "₹2,444"),
        (300_000, "₹3,000"),
        (99_999, "₹1,000"),
        (18_400_000, "₹1,84,000"),
        (1_000_000_000, "₹1,00,00,000"),
    ],
)
def test_format_paise_as_whole_rupees_rounds_half_up_and_groups_the_indian_way(
    amount_in_paise: int, expected_text: str
) -> None:
    """₹3,666.67 shows as ₹3,667 and ₹1,84,000 keeps its lakh grouping."""
    assert format_paise_as_whole_rupees(amount_in_paise) == expected_text


@pytest.mark.parametrize("not_paise", [True, 3.5, "100"])
def test_format_paise_as_whole_rupees_refuses_anything_but_an_int(not_paise: object) -> None:
    """A float or text never becomes money text."""
    with pytest.raises(TypeError, match="int"):
        format_paise_as_whole_rupees(not_paise)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("whole_number", "expected_text"),
    [(7, "7"), (999, "999"), (1000, "1,000"), (12345, "12,345"), (123456, "1,23,456")],
)
def test_group_digits_the_indian_way_groups_pairs_above_the_last_three(
    whole_number: int, expected_text: str
) -> None:
    """Three digits, then pairs."""
    assert group_digits_the_indian_way(whole_number) == expected_text


def test_group_digits_the_indian_way_refuses_a_negative_number() -> None:
    """Money text is never negative."""
    with pytest.raises(ValueError, match="non-negative"):
        group_digits_the_indian_way(-1)


@pytest.mark.parametrize("not_a_whole_number", [False, 2.0])
def test_group_digits_the_indian_way_refuses_a_bool_or_float(not_a_whole_number: object) -> None:
    """Only an int is grouped."""
    with pytest.raises(TypeError, match="whole number"):
        group_digits_the_indian_way(not_a_whole_number)  # type: ignore[arg-type]
