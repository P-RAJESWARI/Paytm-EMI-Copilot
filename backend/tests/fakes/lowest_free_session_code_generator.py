"""A SessionCodeGenerator test double that always picks the lowest free code."""

from emi_copilot.core.session_code_generator import ALL_SESSION_CODES


class LowestFreeSessionCodeGenerator:
    """Gives 0000, then 0001, ...; set is_exhausted to make it report that no code is free."""

    def __init__(self) -> None:
        """Starts with every code available."""
        self.is_exhausted = False
        self.taken_codes_seen: list[frozenset[str]] = []

    def pick_free_code(self, taken_codes: frozenset[str]) -> str | None:
        """Records what was taken and returns the lowest free code, or None when exhausted."""
        self.taken_codes_seen.append(taken_codes)
        if self.is_exhausted:
            return None
        return next(code for code in ALL_SESSION_CODES if code not in taken_codes)
