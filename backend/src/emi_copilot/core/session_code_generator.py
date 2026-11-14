"""Injectable picker of 4-digit session codes, so tests can choose codes deterministically."""

import random
from typing import Protocol

SESSION_CODE_COUNT = 10_000
"""Every code from 0000 to 9999."""

ALL_SESSION_CODES = tuple(f"{code_number:04d}" for code_number in range(SESSION_CODE_COUNT))


class SessionCodeGenerator(Protocol):
    """Anything that can pick a 4-digit code that is not already taken."""

    def pick_free_code(self, taken_codes: frozenset[str]) -> str | None:
        """Returns a code from 0000 to 9999 not in taken_codes, or None when all are taken."""
        ...


class RandomSessionCodeGenerator:
    """Picks uniformly among the free codes, so neighbouring sales get unrelated numbers.

    A code is a display label, never a credential, so it needs no cryptographic strength; the
    system source is used anyway so codes cannot be predicted from earlier ones.
    """

    def __init__(self, random_source: random.Random | None = None) -> None:
        """Uses the given source (seeded in tests) or the operating system's randomness."""
        self._random_source = random_source or random.SystemRandom()

    def pick_free_code(self, taken_codes: frozenset[str]) -> str | None:
        """Returns a random free code, or None when every one of the 10,000 is taken."""
        free_codes = [code for code in ALL_SESSION_CODES if code not in taken_codes]
        if not free_codes:
            return None
        return self._random_source.choice(free_codes)
