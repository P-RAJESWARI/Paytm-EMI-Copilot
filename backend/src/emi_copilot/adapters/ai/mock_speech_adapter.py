"""MockSpeechAdapter: labelled stand-in for speech; nothing leaves the process (rule 10)."""

import io
import logging
import wave
from types import MappingProxyType
from typing import override

from emi_copilot.adapters.ai.ai_types import SpeechAudio, SpeechTranscript, SynthesisedAudio
from emi_copilot.adapters.ai.speech_port import SpeechPort
from emi_copilot.domain.customer_sessions import CustomerLanguage

MOCK_SPEECH_ACTIVE_WARNING = (
    "MockSpeechAdapter active: every recording gives a fixed transcript and speech is silent"
)
WAV_MEDIA_TYPE = "audio/wav"
SILENT_WAV_SAMPLE_RATE_IN_HERTZ = 8_000
SILENT_WAV_DURATION_IN_MILLISECONDS = 500
_BYTES_PER_SAMPLE = 2
_MILLISECONDS_PER_SECOND = 1_000

# The design's spoken budget (DESIGN_SPEC.md section 4), written with digits so it can be parsed.
FIXED_TRANSCRIPTS_BY_LANGUAGE = MappingProxyType(
    {
        CustomerLanguage.ENGLISH: "₹3,000 a month",
        # draft: needs native review
        CustomerLanguage.TAMIL: "மாதம் ₹3,000",
    }
)
LANGUAGE_CODES_BY_LANGUAGE = MappingProxyType(
    {CustomerLanguage.ENGLISH: "en-IN", CustomerLanguage.TAMIL: "ta-IN"}
)

mock_speech_logger = logging.getLogger(__name__)


def build_silent_wav() -> bytes:
    """Builds a short, valid, silent mono 16-bit WAV file in memory with the standard library."""
    frame_count = (
        SILENT_WAV_SAMPLE_RATE_IN_HERTZ
        * SILENT_WAV_DURATION_IN_MILLISECONDS
        // _MILLISECONDS_PER_SECOND
    )
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_writer:
        wav_writer.setnchannels(1)
        wav_writer.setsampwidth(_BYTES_PER_SAMPLE)
        wav_writer.setframerate(SILENT_WAV_SAMPLE_RATE_IN_HERTZ)
        wav_writer.writeframes(bytes(frame_count * _BYTES_PER_SAMPLE))
    return buffer.getvalue()


# Pattern: Adapter (Mock). Implements SpeechPort without any network, so the voice screens can be
# built, tested and demonstrated before or without the Sarvam key.
class MockSpeechAdapter(SpeechPort):
    """Hears the design's ₹3,000 budget in every recording and speaks half a second of silence."""

    def __init__(self) -> None:
        """Announces in the startup log that speech is mocked."""
        mock_speech_logger.warning(MOCK_SPEECH_ACTIVE_WARNING, extra={"speech_adapter": "mock"})

    @override
    def transcribe(self, audio: SpeechAudio, language: CustomerLanguage) -> SpeechTranscript:
        """Ignores the audio and gives the fixed transcript of the chosen language."""
        return SpeechTranscript(
            transcript=FIXED_TRANSCRIPTS_BY_LANGUAGE[language],
            detected_language_code=LANGUAGE_CODES_BY_LANGUAGE[language],
            audio_duration_in_seconds=None,
        )

    @override
    def synthesise(self, text: str, language: CustomerLanguage) -> SynthesisedAudio:
        """Gives a silent WAV whatever the text, so audio playback can be exercised offline."""
        return SynthesisedAudio(content=build_silent_wav(), media_type=WAV_MEDIA_TYPE)
