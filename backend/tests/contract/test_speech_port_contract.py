"""SpeechPort contract: the labelled Mock and the Sarvam adapter (on fixtures) behave the same.

The Sarvam side answers from documented-shape fixtures [Verify] through httpx.MockTransport, so
no test reaches the network.
"""

from collections.abc import Callable

import pytest

from emi_copilot.adapters.ai.ai_types import SpeechAudio
from emi_copilot.adapters.ai.mock_speech_adapter import MockSpeechAdapter
from emi_copilot.adapters.ai.speech_port import SpeechPort
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.speech import SpokenAmountParser
from tests.sarvam_builders import (
    build_sarvam_speech_adapter,
    build_scripted_client,
    fixture_response,
)

RECORDING = SpeechAudio(content=b"synthetic-recording", media_type="audio/webm")


def build_sarvam_speech_port() -> SpeechPort:
    """Builds the Sarvam adapter answering from the success fixtures."""
    return build_sarvam_speech_adapter(
        build_scripted_client([fixture_response(200, "stt_success.json")]),
        build_scripted_client([fixture_response(200, "tts_success.json")]),
    )


SPEECH_PORT_BUILDERS: dict[str, Callable[[], SpeechPort]] = {
    "mock": MockSpeechAdapter,
    "sarvam": build_sarvam_speech_port,
}


@pytest.fixture(params=sorted(SPEECH_PORT_BUILDERS))
def speech_port(request: pytest.FixtureRequest) -> SpeechPort:
    """Gives each SpeechPort implementation in turn."""
    port_name: str = request.param
    return SPEECH_PORT_BUILDERS[port_name]()


def test_speech_port_transcribe_gives_text_the_budget_parser_reads(speech_port: SpeechPort) -> None:
    """Both give a transcript of the design's ₹3,000 budget, read the same way."""
    transcript = speech_port.transcribe(RECORDING, CustomerLanguage.ENGLISH)
    assert SpokenAmountParser().parse_amount_in_paise(transcript.transcript) == 300_000
    assert transcript.detected_language_code == "en-IN"
    assert transcript.audio_duration_in_seconds is None


def test_speech_port_synthesise_gives_non_empty_audio(speech_port: SpeechPort) -> None:
    """Both give playable bytes with an audio media type."""
    audio = speech_port.synthesise("₹3,667 each month for 6 months.", CustomerLanguage.TAMIL)
    assert audio.content
    assert audio.media_type.startswith("audio/")
