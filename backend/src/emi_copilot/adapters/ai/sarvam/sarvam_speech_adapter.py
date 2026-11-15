"""SarvamSpeechAdapter: Sarvam speech-to-text (saaras) and text-to-speech (bulbul), as SpeechPort.

Audio is held only as bytes in memory: the multipart body is built from them and the answer's
base64 audio is decoded in memory, so nothing is ever written to disk (voice is never stored).
Only sizes, latency and Sarvam's request id are logged, never audio, text or the key.
"""

import base64
import binascii
import logging
import re
from dataclasses import dataclass
from typing import override

import httpx
from pydantic import SecretStr

from emi_copilot.adapters.ai.ai_types import SpeechAudio, SpeechTranscript, SynthesisedAudio
from emi_copilot.adapters.ai.sarvam.sarvam_api_definitions import (
    LANGUAGE_CODES_BY_LANGUAGE,
    SPEECH_TO_TEXT_DEPENDENCY_NAME,
    SPEECH_TO_TEXT_PATH,
    SUBSCRIPTION_KEY_HEADER,
    TEXT_TO_SPEECH_DEPENDENCY_NAME,
    TEXT_TO_SPEECH_MAXIMUM_CHARACTERS,
    TEXT_TO_SPEECH_MEDIA_TYPE,
    TEXT_TO_SPEECH_OUTPUT_AUDIO_CODEC,
    TEXT_TO_SPEECH_PATH,
)
from emi_copilot.adapters.ai.sarvam.sarvam_error_translator import (
    SPEECH_FAILURE_ERRORS,
    SarvamErrorTranslator,
    read_text_field,
)
from emi_copilot.adapters.ai.sarvam.sarvam_request_sender import SarvamAnswer, SarvamRequestSender
from emi_copilot.adapters.ai.speech_port import SpeechPort
from emi_copilot.config.ai_settings import AiSettings
from emi_copilot.core.resilient_http_client import ResilientHttpClient
from emi_copilot.domain.ai_errors import SpeechTextTooLongError
from emi_copilot.domain.customer_sessions import CustomerLanguage

RECORDING_FILE_STEM = "recording"
_SIMPLE_SUBTYPE_PATTERN = re.compile(r"[a-z0-9]+")

sarvam_speech_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SarvamSpeechHttpClients:
    """One client and breaker per speech capability, so a failing one trips alone."""

    speech_to_text: ResilientHttpClient
    text_to_speech: ResilientHttpClient


def build_recording_file_name(media_type: str) -> str:
    """Names the in-memory upload by its subtype ("audio/webm;codecs=opus" gives recording.webm).

    [Verify] whether Sarvam reads the format from the file name, the part type or the bytes.
    """
    subtype = media_type.split(";", maxsplit=1)[0].split("/", maxsplit=1)[-1].strip().lower()
    if _SIMPLE_SUBTYPE_PATTERN.fullmatch(subtype) is None:
        return RECORDING_FILE_STEM
    return f"{RECORDING_FILE_STEM}.{subtype}"


def decode_first_audio(document: dict[str, object]) -> bytes | None:
    """Decodes audios[0] from base64 in memory; None when it is missing, empty or not base64."""
    audios = document.get("audios")
    if not isinstance(audios, list) or not audios or not isinstance(audios[0], str):
        return None
    try:
        audio_bytes = base64.b64decode(audios[0], validate=True)
    except binascii.Error:
        return None
    return audio_bytes or None


# Pattern: Adapter. Translates SpeechPort calls into Sarvam's documented requests and its answers
# and failures into our typed values and errors; every Sarvam name stays inside sarvam/.
class SarvamSpeechAdapter(SpeechPort):
    """Calls Sarvam once per request, never retried: each call costs credits; voice is optional."""

    def __init__(
        self, settings: AiSettings, api_key: SecretStr, http_clients: SarvamSpeechHttpClients
    ) -> None:
        """Keeps the settings (models, speakers), the key and the two capability clients."""
        self._settings = settings
        self._api_key = api_key
        self._http_clients = http_clients
        self._translator = SarvamErrorTranslator()
        self._sender = SarvamRequestSender(self._translator)

    @override
    def transcribe(self, audio: SpeechAudio, language: CustomerLanguage) -> SpeechTranscript:
        """Sends the recording as multipart built in memory; the duration is not known here."""
        request = httpx.Request(
            "POST",
            self._settings.sarvam_base_url + SPEECH_TO_TEXT_PATH,
            headers=self._authentication_headers(),
            data={
                "model": self._settings.sarvam_speech_to_text_model,
                "language_code": LANGUAGE_CODES_BY_LANGUAGE[language],
            },
            files={
                "file": (
                    build_recording_file_name(audio.media_type),
                    audio.content,
                    audio.media_type,
                )
            },
        )
        answer = self._send(
            self._http_clients.speech_to_text, request, SPEECH_TO_TEXT_DEPENDENCY_NAME
        )
        transcript = read_text_field(answer.document, "transcript")
        if transcript is None:
            raise self._translator.translate_unusable_answer(SPEECH_FAILURE_ERRORS)
        self._log_completed(SPEECH_TO_TEXT_DEPENDENCY_NAME, answer, sent_size=len(audio.content))
        return SpeechTranscript(
            transcript=transcript,
            detected_language_code=read_text_field(answer.document, "language_code"),
            audio_duration_in_seconds=None,
        )

    @override
    def synthesise(self, text: str, language: CustomerLanguage) -> SynthesisedAudio:
        """Sends the shown text for mp3 speech; text over 2,500 characters is refused unsent."""
        if len(text) > TEXT_TO_SPEECH_MAXIMUM_CHARACTERS:
            raise SpeechTextTooLongError(
                f"Text-to-speech takes at most {TEXT_TO_SPEECH_MAXIMUM_CHARACTERS} characters."
            )
        request = httpx.Request(
            "POST",
            self._settings.sarvam_base_url + TEXT_TO_SPEECH_PATH,
            headers=self._authentication_headers(),
            json={
                "text": text,
                "language_code": LANGUAGE_CODES_BY_LANGUAGE[language],
                "model": self._settings.sarvam_text_to_speech_model,
                "speaker": self._speaker_for(language),
                "output_audio_codec": TEXT_TO_SPEECH_OUTPUT_AUDIO_CODEC,
            },
        )
        answer = self._send(
            self._http_clients.text_to_speech, request, TEXT_TO_SPEECH_DEPENDENCY_NAME
        )
        audio_bytes = decode_first_audio(answer.document)
        if audio_bytes is None:
            raise self._translator.translate_unusable_answer(SPEECH_FAILURE_ERRORS)
        self._log_completed(TEXT_TO_SPEECH_DEPENDENCY_NAME, answer, sent_size=len(text))
        return SynthesisedAudio(content=audio_bytes, media_type=TEXT_TO_SPEECH_MEDIA_TYPE)

    def _authentication_headers(self) -> dict[str, str]:
        """Gives the documented subscription key header; it is never logged."""
        return {SUBSCRIPTION_KEY_HEADER: self._api_key.get_secret_value()}

    def _speaker_for(self, language: CustomerLanguage) -> str:
        """Gives the configured bulbul:v3 speaker of the language [Verify]."""
        if language is CustomerLanguage.TAMIL:
            return self._settings.sarvam_text_to_speech_tamil_speaker
        return self._settings.sarvam_text_to_speech_english_speaker

    def _send(
        self, http_client: ResilientHttpClient, request: httpx.Request, dependency_name: str
    ) -> SarvamAnswer:
        """Sends one speech request exactly once through the shared sender."""
        return self._sender.send(http_client, request, dependency_name, SPEECH_FAILURE_ERRORS)

    def _log_completed(self, dependency_name: str, answer: SarvamAnswer, *, sent_size: int) -> None:
        """Logs the event with sizes, latency and request id only; never audio or text."""
        sarvam_speech_logger.info(
            "sarvam speech call completed",
            extra={
                "dependency_name": dependency_name,
                "sent_size": sent_size,
                "latency_in_milliseconds": answer.latency_in_milliseconds,
                "sarvam_request_id": answer.request_id,
            },
        )
