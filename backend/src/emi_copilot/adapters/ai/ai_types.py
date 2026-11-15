"""Typed values that cross the AI ports; every provider's shapes are translated into these.

Audio and the customer's transcript are kept out of repr, so a stray log line cannot carry them
(voice is never stored, security-and-compliance.md section 2).
"""

import json
from dataclasses import dataclass, field
from decimal import Decimal

from emi_copilot.domain.ai_errors import InvalidAiValueError
from emi_copilot.domain.customer_sessions import CustomerLanguage

AUDIO_MEDIA_TYPE_PREFIX = "audio/"


def _require_audio(content: bytes, media_type: str) -> None:
    """Rejects empty audio and a media type that is not audio/*."""
    if not isinstance(content, bytes) or not content:
        raise InvalidAiValueError("Audio content must be non-empty bytes.")
    if not media_type.startswith(AUDIO_MEDIA_TYPE_PREFIX):
        raise InvalidAiValueError("Audio media type must start with audio/.")


@dataclass(frozen=True, slots=True)
class SpeechAudio:
    """One short recording of the customer, held in memory only and never written to disk."""

    content: bytes = field(repr=False)
    media_type: str

    def __post_init__(self) -> None:
        """Rejects empty audio or a non-audio media type."""
        _require_audio(self.content, self.media_type)


@dataclass(frozen=True, slots=True)
class SpeechTranscript:
    """What the customer said, as text; the customer still confirms any amount on screen."""

    transcript: str = field(repr=False)
    detected_language_code: str | None
    audio_duration_in_seconds: Decimal | None

    def __post_init__(self) -> None:
        """Rejects a duration that is not a non-negative Decimal."""
        duration = self.audio_duration_in_seconds
        if duration is not None and (not isinstance(duration, Decimal) or duration < 0):
            raise InvalidAiValueError("Audio duration must be a non-negative Decimal.")


@dataclass(frozen=True, slots=True)
class SynthesisedAudio:
    """Speech made from text that was already shown on screen, ready to send to the phone."""

    content: bytes = field(repr=False)
    media_type: str

    def __post_init__(self) -> None:
        """Rejects empty audio or a non-audio media type."""
        _require_audio(self.content, self.media_type)


@dataclass(frozen=True, slots=True)
class AiTextRequest:
    """What an AI text writer is given: fixed instructions and a JSON object of typed facts.

    The facts are data, never instructions, and hold no personal data (ADR 0026). There is
    deliberately no field for tools: AI components cannot call any function (CLAUDE.md rule 1).
    """

    system_instruction: str
    structured_facts_json: str
    language: CustomerLanguage

    def __post_init__(self) -> None:
        """Rejects blank instructions and facts that are not one JSON object."""
        if not self.system_instruction.strip():
            raise InvalidAiValueError("The system instruction must not be blank.")
        try:
            facts = json.loads(self.structured_facts_json)
        except json.JSONDecodeError as decode_error:
            raise InvalidAiValueError("The structured facts must be valid JSON.") from decode_error
        if not isinstance(facts, dict):
            raise InvalidAiValueError("The structured facts must be one JSON object.")


@dataclass(frozen=True, slots=True)
class AiTextCompletion:
    """Text an AI writer produced, with the usage needed for cost estimates; not yet audited."""

    text: str
    model_name: str
    input_token_count: int
    output_token_count: int
    finish_reason: str

    def __post_init__(self) -> None:
        """Rejects a blank model name and negative token counts."""
        if not self.model_name.strip():
            raise InvalidAiValueError("The model name must not be blank.")
        if self.input_token_count < 0 or self.output_token_count < 0:
            raise InvalidAiValueError("Token counts must not be negative.")
