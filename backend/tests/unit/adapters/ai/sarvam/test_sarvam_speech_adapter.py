"""SarvamSpeechAdapter: documented requests, one attempt per call, typed errors, nothing on disk."""

import base64
import builtins
import json
import logging
import tempfile

import httpx
import pytest
from pydantic import SecretStr

from emi_copilot.adapters.ai.ai_types import SpeechAudio
from emi_copilot.adapters.ai.sarvam.sarvam_speech_adapter import (
    SarvamSpeechAdapter,
    SarvamSpeechHttpClients,
    build_recording_file_name,
)
from emi_copilot.config.ai_settings import AiSettings
from emi_copilot.core.circuit_breaker import CircuitState
from emi_copilot.domain.ai_errors import (
    SpeechTextTooLongError,
    SpeechTimeoutError,
    SpeechUnavailableError,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage
from tests.sarvam_builders import (
    SYNTHETIC_SARVAM_KEY,
    ScriptedSarvamClient,
    ScriptedSarvamOutcome,
    build_sarvam_speech_adapter,
    build_scripted_client,
    fixture_response,
)

RECORDING = SpeechAudio(content=b"synthetic-webm-recording", media_type="audio/webm;codecs=opus")
# The tts_success.json audio: an ID3 marker and zero bytes, not real mp3.
SYNTHETIC_MP3_BYTES = b"ID3" + bytes(21)
SHOWN_TEXT = "No-cost EMI: you pay ₹3,667 each month for 6 months."


def build_adapter(
    outcomes: list[ScriptedSarvamOutcome],
    text_to_speech_outcomes: list[ScriptedSarvamOutcome] | None = None,
) -> tuple[SarvamSpeechAdapter, ScriptedSarvamClient, ScriptedSarvamClient]:
    """Builds the adapter; text-to-speech replays the same outcomes unless given its own."""
    speech_to_text = build_scripted_client(outcomes, "sarvam-speech-to-text")
    text_to_speech = build_scripted_client(
        outcomes if text_to_speech_outcomes is None else text_to_speech_outcomes,
        "sarvam-text-to-speech",
    )
    return (
        build_sarvam_speech_adapter(speech_to_text, text_to_speech),
        speech_to_text,
        text_to_speech,
    )


def test_sarvam_transcribe_sends_the_key_header_saaras_and_the_language_as_multipart() -> None:
    """The documented fields only: file, model and language_code, with api-subscription-key."""
    adapter, speech_to_text, _ = build_adapter([fixture_response(200, "stt_success.json")])
    transcript = adapter.transcribe(RECORDING, CustomerLanguage.TAMIL)
    (request,) = speech_to_text.server.received_requests
    assert request.url == "https://api.sarvam.ai/speech-to-text"
    assert request.headers["api-subscription-key"] == SYNTHETIC_SARVAM_KEY
    assert "authorization" not in request.headers
    body = request.content
    assert b'name="model"\r\n\r\nsaaras:v4' in body
    assert b'name="language_code"\r\n\r\nta-IN' in body
    assert b'name="file"; filename="recording.webm"' in body
    assert b"synthetic-webm-recording" in body
    assert transcript.transcript == "₹3,000 a month"
    assert transcript.detected_language_code == "en-IN"
    assert transcript.audio_duration_in_seconds is None


def test_sarvam_synthesise_sends_exactly_the_documented_json_and_decodes_mp3() -> None:
    """text, language_code, bulbul:v3, the speaker and mp3; the base64 audio is decoded here."""
    adapter, _, text_to_speech = build_adapter([fixture_response(200, "tts_success.json")])
    audio = adapter.synthesise(SHOWN_TEXT, CustomerLanguage.ENGLISH)
    (request,) = text_to_speech.server.received_requests
    assert request.url == "https://api.sarvam.ai/text-to-speech"
    assert request.headers["api-subscription-key"] == SYNTHETIC_SARVAM_KEY
    assert json.loads(request.content) == {
        "text": SHOWN_TEXT,
        "language_code": "en-IN",
        "model": "bulbul:v3",
        "speaker": "shubh",
        "output_audio_codec": "mp3",
    }
    assert audio.media_type == "audio/mpeg"
    assert audio.content == SYNTHETIC_MP3_BYTES


def test_sarvam_synthesise_in_tamil_uses_the_tamil_speaker() -> None:
    """Each language has its own configured speaker."""
    text_to_speech = build_scripted_client([fixture_response(200, "tts_success.json")])
    adapter = SarvamSpeechAdapter(
        AiSettings(sarvam_text_to_speech_tamil_speaker="synthetic-tamil-speaker"),
        SecretStr(SYNTHETIC_SARVAM_KEY),
        SarvamSpeechHttpClients(
            speech_to_text=build_scripted_client([]).client, text_to_speech=text_to_speech.client
        ),
    )
    adapter.synthesise(SHOWN_TEXT, CustomerLanguage.TAMIL)
    body = json.loads(text_to_speech.server.received_requests[0].content)
    assert (body["speaker"], body["language_code"]) == ("synthetic-tamil-speaker", "ta-IN")


@pytest.mark.parametrize("timeout_error", [httpx.ReadTimeout, httpx.ConnectTimeout])
def test_sarvam_transcribe_timeout_raises_speech_timeout_after_one_attempt(
    timeout_error: type[httpx.RequestError],
) -> None:
    """Calls cost credits and a fallback exists, so a timeout is never retried."""
    adapter, speech_to_text, _ = build_adapter([timeout_error])
    with pytest.raises(SpeechTimeoutError):
        adapter.transcribe(RECORDING, CustomerLanguage.ENGLISH)
    assert len(speech_to_text.server.received_requests) == 1


def test_sarvam_open_breaker_short_circuits_without_sending() -> None:
    """After the failure threshold, calls fail fast and nothing reaches Sarvam."""
    adapter, speech_to_text, _ = build_adapter([httpx.Response(500)])
    for _ in range(2):
        with pytest.raises(SpeechUnavailableError, match="could not serve"):
            adapter.transcribe(RECORDING, CustomerLanguage.ENGLISH)
    assert speech_to_text.circuit_breaker.state is CircuitState.OPEN
    with pytest.raises(SpeechUnavailableError, match="circuit is open"):
        adapter.transcribe(RECORDING, CustomerLanguage.ENGLISH)
    assert len(speech_to_text.server.received_requests) == 2


def test_sarvam_synthesise_over_2500_characters_is_refused_before_sending() -> None:
    """No credit is spent on text Sarvam would refuse; exactly 2,500 is still sent."""
    adapter, _, text_to_speech = build_adapter([fixture_response(200, "tts_success.json")])
    with pytest.raises(SpeechTextTooLongError):
        adapter.synthesise("a" * 2_501, CustomerLanguage.ENGLISH)
    assert text_to_speech.server.received_requests == []
    adapter.synthesise("a" * 2_500, CustomerLanguage.ENGLISH)
    assert len(text_to_speech.server.received_requests) == 1


@pytest.mark.parametrize(
    ("response", "expected_message"),
    [
        (fixture_response(403, "error_403.json"), "SARVAM_API_KEY"),
        (fixture_response(429, "error_429.json"), "rate limit"),
        (
            httpx.Response(429, json={"error": {"code": "insufficient_quota_error"}}),
            "credits are used up",
        ),
        (httpx.Response(400, text="not json"), "status 400"),
    ],
)
def test_sarvam_refusal_raises_speech_unavailable_without_the_vendor_message(
    response: httpx.Response, expected_message: str
) -> None:
    """Our own English reason only; Sarvam's message never leaves the adapter."""
    adapter, _, _ = build_adapter([response])
    with pytest.raises(SpeechUnavailableError, match=expected_message) as raised:
        adapter.transcribe(RECORDING, CustomerLanguage.ENGLISH)
    assert "Synthetic" not in raised.value.detail


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json=["a list"]),
        httpx.Response(200, json={"language_code": "en-IN"}),
    ],
)
def test_sarvam_transcribe_answer_without_a_transcript_is_unavailable(
    response: httpx.Response,
) -> None:
    """A success answer without the documented field is a failure, never a guess."""
    adapter, _, _ = build_adapter([response])
    with pytest.raises(SpeechUnavailableError, match="documented fields"):
        adapter.transcribe(RECORDING, CustomerLanguage.ENGLISH)


@pytest.mark.parametrize(
    "body",
    [{}, {"audios": []}, {"audios": [7]}, {"audios": ["not base64!"]}, {"audios": [""]}],
)
def test_sarvam_synthesise_answer_without_usable_audio_is_unavailable(
    body: dict[str, object],
) -> None:
    """Missing, empty or undecodable audio is a failure."""
    adapter, _, _ = build_adapter([httpx.Response(200, json=body)])
    with pytest.raises(SpeechUnavailableError, match="documented fields"):
        adapter.synthesise(SHOWN_TEXT, CustomerLanguage.ENGLISH)


def test_sarvam_speech_audio_never_touches_the_disk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Voice is never stored: no file is opened and no temporary file is made, either way."""

    def refuse_disk(*_arguments: object, **_keyword_arguments: object) -> None:
        """Fails the test if anything tries to use the disk."""
        raise AssertionError("audio must stay in memory")

    adapter, _, _ = build_adapter(
        [fixture_response(200, "stt_success.json")], [fixture_response(200, "tts_success.json")]
    )
    for name in ("TemporaryFile", "NamedTemporaryFile", "SpooledTemporaryFile", "mkstemp"):
        monkeypatch.setattr(tempfile, name, refuse_disk)
    monkeypatch.setattr(builtins, "open", refuse_disk)
    adapter.transcribe(RECORDING, CustomerLanguage.ENGLISH)
    adapter.synthesise(SHOWN_TEXT, CustomerLanguage.ENGLISH)


def test_sarvam_speech_logs_sizes_and_request_id_but_never_the_key_audio_or_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log events, not payloads; the key is never logged, even on a refusal."""
    adapter, _, _ = build_adapter(
        [fixture_response(200, "stt_success.json"), fixture_response(403, "error_403.json")],
        [fixture_response(200, "tts_success.json")],
    )
    with caplog.at_level(logging.DEBUG):
        adapter.transcribe(RECORDING, CustomerLanguage.ENGLISH)
        adapter.synthesise(SHOWN_TEXT, CustomerLanguage.ENGLISH)
        with pytest.raises(SpeechUnavailableError):
            adapter.transcribe(RECORDING, CustomerLanguage.ENGLISH)
    logged = caplog.text + " ".join(str(record.__dict__) for record in caplog.records)
    for secret_or_payload in (SYNTHETIC_SARVAM_KEY, "synthetic-webm-recording", "3,667", "3,000"):
        assert secret_or_payload not in logged
    assert "synthetic-stt-request-0001" in logged
    assert "invalid_api_key_error" in logged
    assert base64.b64encode(b"ID3").decode() not in logged


@pytest.mark.parametrize(
    ("media_type", "expected_name"),
    [
        ("audio/webm;codecs=opus", "recording.webm"),
        ("audio/wav", "recording.wav"),
        ("audio/x-m4a", "recording"),
    ],
)
def test_build_recording_file_name_uses_a_simple_subtype_only(
    media_type: str, expected_name: str
) -> None:
    """The upload is named from the media type; anything unusual gets no extension."""
    assert build_recording_file_name(media_type) == expected_name
