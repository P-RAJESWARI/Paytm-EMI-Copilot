"""AI port values refuse empty or malformed content, and keep audio out of repr."""

from decimal import Decimal

import pytest

from emi_copilot.adapters.ai.ai_types import (
    AiTextCompletion,
    AiTextRequest,
    SpeechAudio,
    SpeechTranscript,
    SynthesisedAudio,
)
from emi_copilot.domain.ai_errors import InvalidAiValueError
from emi_copilot.domain.customer_sessions import CustomerLanguage

SYNTHETIC_AUDIO = b"RIFF-synthetic-audio"


@pytest.mark.parametrize("audio_class", [SpeechAudio, SynthesisedAudio])
def test_audio_value_with_content_keeps_the_bytes_out_of_repr(
    audio_class: type[SpeechAudio] | type[SynthesisedAudio],
) -> None:
    """Voice is never logged: printing the value shows its media type only."""
    audio = audio_class(content=SYNTHETIC_AUDIO, media_type="audio/webm")
    assert audio.content == SYNTHETIC_AUDIO
    assert "RIFF" not in repr(audio)


@pytest.mark.parametrize(
    ("content", "media_type"),
    [(b"", "audio/webm"), (SYNTHETIC_AUDIO, "video/mp4"), (SYNTHETIC_AUDIO, "")],
)
@pytest.mark.parametrize("audio_class", [SpeechAudio, SynthesisedAudio])
def test_audio_value_empty_or_not_audio_is_rejected(
    audio_class: type[SpeechAudio] | type[SynthesisedAudio], content: bytes, media_type: str
) -> None:
    """Empty recordings and non-audio uploads never reach a provider."""
    with pytest.raises(InvalidAiValueError):
        audio_class(content=content, media_type=media_type)


def test_speech_transcript_keeps_the_customer_words_out_of_repr() -> None:
    """What the customer said is not printed by accident."""
    transcript = SpeechTranscript(
        transcript="₹3,000 a month",
        detected_language_code="en-IN",
        audio_duration_in_seconds=Decimal("2.5"),
    )
    assert "3,000" not in repr(transcript)
    assert transcript.audio_duration_in_seconds == Decimal("2.5")


@pytest.mark.parametrize("duration", [Decimal("-0.1"), 2.5])
def test_speech_transcript_with_negative_or_float_duration_is_rejected(duration: object) -> None:
    """Durations feed cost estimates, so they are non-negative Decimals."""
    with pytest.raises(InvalidAiValueError):
        SpeechTranscript(
            transcript="",
            detected_language_code=None,
            audio_duration_in_seconds=duration,  # type: ignore[arg-type]
        )


def test_ai_text_request_with_a_json_object_of_facts_is_accepted() -> None:
    """Facts are one JSON object of data, beside fixed instructions."""
    request = AiTextRequest(
        system_instruction="Explain the plan.",
        structured_facts_json='{"monthlyAmount": "₹3,667"}',
        language=CustomerLanguage.TAMIL,
    )
    assert request.language is CustomerLanguage.TAMIL


@pytest.mark.parametrize(
    ("system_instruction", "structured_facts_json"),
    [("  ", "{}"), ("Explain.", "not json"), ("Explain.", '["a list"]')],
)
def test_ai_text_request_with_blank_instruction_or_non_object_facts_is_rejected(
    system_instruction: str, structured_facts_json: str
) -> None:
    """A malformed request is a programming error, raised before any provider is called."""
    with pytest.raises(InvalidAiValueError):
        AiTextRequest(
            system_instruction=system_instruction,
            structured_facts_json=structured_facts_json,
            language=CustomerLanguage.ENGLISH,
        )


@pytest.mark.parametrize(
    ("model_name", "input_token_count", "output_token_count"),
    [(" ", 1, 1), ("mock", -1, 1), ("mock", 1, -1)],
)
def test_ai_text_completion_with_blank_model_or_negative_tokens_is_rejected(
    model_name: str, input_token_count: int, output_token_count: int
) -> None:
    """Usage numbers feed cost estimates, so they are never negative."""
    with pytest.raises(InvalidAiValueError):
        AiTextCompletion(
            text="text",
            model_name=model_name,
            input_token_count=input_token_count,
            output_token_count=output_token_count,
            finish_reason="stop",
        )
