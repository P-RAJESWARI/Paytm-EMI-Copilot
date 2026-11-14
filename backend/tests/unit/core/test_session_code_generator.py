"""RandomSessionCodeGenerator: picks only free four-digit codes and says when none is left."""

import random

from emi_copilot.core.session_code_generator import (
    ALL_SESSION_CODES,
    SESSION_CODE_COUNT,
    RandomSessionCodeGenerator,
)


def test_all_session_codes_are_the_ten_thousand_four_digit_labels() -> None:
    """0000 to 9999, leading zeros kept."""
    assert len(ALL_SESSION_CODES) == SESSION_CODE_COUNT
    assert (ALL_SESSION_CODES[0], ALL_SESSION_CODES[42], ALL_SESSION_CODES[-1]) == (
        "0000",
        "0042",
        "9999",
    )


def test_pick_free_code_never_returns_a_taken_code() -> None:
    """With all but one code taken, the one free code is the only possible answer."""
    taken_codes = frozenset(ALL_SESSION_CODES) - {"4821"}
    generator = RandomSessionCodeGenerator(random.Random(7))  # noqa: S311 - display label only
    assert generator.pick_free_code(taken_codes) == "4821"


def test_pick_free_code_with_a_seeded_source_is_deterministic() -> None:
    """Tests can reproduce a pick by seeding the source."""
    first_pick = RandomSessionCodeGenerator(random.Random(11)).pick_free_code(frozenset())  # noqa: S311
    second_pick = RandomSessionCodeGenerator(random.Random(11)).pick_free_code(frozenset())  # noqa: S311
    assert first_pick == second_pick
    assert first_pick in ALL_SESSION_CODES


def test_pick_free_code_when_every_code_is_taken_returns_none() -> None:
    """The caller turns this into SessionCodesExhaustedError."""
    generator = RandomSessionCodeGenerator()
    assert generator.pick_free_code(frozenset(ALL_SESSION_CODES)) is None


def test_default_source_picks_a_valid_code() -> None:
    """Without a seed the operating system's randomness is used."""
    assert RandomSessionCodeGenerator().pick_free_code(frozenset({"0000"})) in ALL_SESSION_CODES
