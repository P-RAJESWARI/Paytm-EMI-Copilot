"""NormalisedText: AI text with every digit made ASCII, still able to quote the original spans."""

import unicodedata
from dataclasses import dataclass


def _normalise_character(character: str) -> str:
    """Applies NFKC to one character, then turns every decimal digit (Tamil too) into ASCII."""
    return "".join(
        str(unicodedata.decimal(compatible_character))
        if unicodedata.decimal(compatible_character, None) is not None
        else compatible_character
        for compatible_character in unicodedata.normalize("NFKC", character)
    )


@dataclass(frozen=True, slots=True)
class NormalisedText:
    """The searchable form of a text and, per searchable character, its original position.

    NFKC is applied one character at a time after canonical composition (NFC), so every
    searchable character maps back to exactly one character of the composed original.
    """

    original_text: str
    searchable_text: str
    original_positions: tuple[int, ...]

    @classmethod
    def from_text(cls, text: str) -> "NormalisedText":
        """Builds the searchable form: NFC, then NFKC and ASCII digits per character."""
        composed_text = unicodedata.normalize("NFC", text)
        searchable_parts: list[str] = []
        original_positions: list[int] = []
        for original_position, character in enumerate(composed_text):
            normalised_character = _normalise_character(character)
            searchable_parts.append(normalised_character)
            original_positions.extend([original_position] * len(normalised_character))
        return cls(composed_text, "".join(searchable_parts), tuple(original_positions))

    def original_span(self, searchable_start: int, searchable_end: int) -> str:
        """Gives the original text behind a non-empty range of the searchable text."""
        first_position = self.original_positions[searchable_start]
        last_position = self.original_positions[searchable_end - 1]
        return self.original_text[first_position : last_position + 1]
