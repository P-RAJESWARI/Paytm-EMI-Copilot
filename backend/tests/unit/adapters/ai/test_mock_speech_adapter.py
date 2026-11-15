"""MockSpeechAdapter announces itself, hears the design's budget and speaks valid silence."""

import io
import logging
import wave

import pytest

from emi_copilot.adapters.ai.ai_types import SpeechAudio
from emi_copilot.adapters.ai.mock_speech_adapter import (
    MOCK_SPEECH_ACTIVE_WARNING,
    MockSpeechAdapter,
    build_silent_wav,
)
from emi_copilot.adapters.ai.speech_port import SpeechPort
from emi_copilot.domain.customer_sessions import CustomerLanguage

SYNTHETIC_RECORDING = SpeechAudio(content=b"synthetic-webm-bytes", media_type="audio/webm")


def test_mock_speech_adapter_built_announces_itself_as_a_mock(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Rule 10: anything not real says so in the startup log."""
    with caplog.at_level(logging.WARNING):
        adapter = MockSpeechAdapter()
    assert isinstance(adapter, SpeechPort)
    assert [record.getMessage() for record in caplog.records] == [MOCK_SPEECH_ACTIVE_WARNING]


@pytest.mark.parametrize(
    ("language", "expected_transcript", "expected_language_code"),
    [
        (CustomerLanguage.ENGLISH, "₹3,000 a month", "en-IN"),
        (CustomerLanguage.TAMIL, "மாதம் ₹3,000", "ta-IN"),
    ],
)
def test_mock_speech_adapter_transcribe_gives_the_fixed_budget_of_the_language(
    language: CustomerLanguage, expected_transcript: str, expected_language_code: str
) -> None:
    """Every recording is heard as the design's ₹3,000 budget, written with digits."""
    transcript = MockSpeechAdapter().transcribe(SYNTHETIC_RECORDING, language)
    assert transcript.transcript == expected_transcript
    assert transcript.detected_language_code == expected_language_code
    assert transcript.audio_duration_in_seconds is None


@pytest.mark.parametrize("language", list(CustomerLanguage))
def test_mock_speech_adapter_synthesise_returns_a_valid_silent_wav(
    language: CustomerLanguage,
) -> None:
    """The audio parses as a mono 16-bit WAV of half a second whose samples are all zero."""
    audio = MockSpeechAdapter().synthesise("Each month ₹3,667 for 6 months.", language)
    assert audio.media_type == "audio/wav"
    with wave.open(io.BytesIO(audio.content), "rb") as wav_reader:
        assert wav_reader.getnchannels() == 1
        assert wav_reader.getsampwidth() == 2
        assert wav_reader.getframerate() == 8_000
        assert wav_reader.getnframes() == 4_000
        assert set(wav_reader.readframes(wav_reader.getnframes())) == {0}


def test_build_silent_wav_is_deterministic() -> None:
    """The same bytes every time, so tests and caches can compare them."""
    assert build_silent_wav() == build_silent_wav()
