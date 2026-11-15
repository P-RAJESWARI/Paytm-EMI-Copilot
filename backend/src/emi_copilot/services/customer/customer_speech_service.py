"""CustomerSpeechService: the customer's voice to text (C2, C8) and shown text to speech (C7).

Voice is optional and advisory: a transcription never changes the budget (the customer still
confirms the amount on screen), and synthesis only speaks text the session was already shown.
Audio stays in memory and is never stored or logged.
"""

import math
import time
from dataclasses import dataclass, field
from enum import StrEnum

from emi_copilot.adapters.ai.ai_types import SpeechAudio, SpeechTranscript, SynthesisedAudio
from emi_copilot.adapters.ai.speech_port import SpeechPort
from emi_copilot.core.clock import Clock
from emi_copilot.domain.ai_errors import (
    AudioFormatUnsupportedError,
    AudioTooLargeError,
    ExplanationNotFoundError,
    InvalidAiValueError,
    SpeechTextTooLongError,
    SpeechUnavailableError,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.speech.spoken_amount_parser import SpokenAmountParser
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.ai.ai_usage_logger import (
    AiCallUsage,
    AiUsageLogger,
    measure_elapsed_milliseconds,
)
from emi_copilot.services.ai.shown_explanation_cache import ShownExplanationCache
from emi_copilot.services.customer.customer_session_access import CustomerSessionAccess
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.sale_expiry import SaleExpiryStep

ACCEPTED_AUDIO_MEDIA_TYPES = frozenset(
    {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav"}
)
SPEECH_OFF_DETAIL = "Speech is switched off; type the amount instead."
COMPLETED_OUTCOME = "COMPLETED"


class SpeechTranscriptionPurpose(StrEnum):
    """Which screen the recording is for: the C2 budget or the C8 teach-back answer."""

    BUDGET = "BUDGET"
    TEACH_BACK = "TEACH_BACK"


@dataclass(frozen=True, slots=True)
class SpeechModelNames:
    """The model names the usage log reports for each speech capability."""

    speech_to_text: str
    text_to_speech: str


@dataclass(frozen=True, slots=True)
class SpeechTranscriptionResult:
    """What was heard, the one amount in it (or None), and whether to ask the customer again."""

    transcript: str = field(repr=False)
    recognised_amount_in_paise: int | None
    is_likely_misheard: bool


def read_base_media_type(content_type: str | None) -> str:
    """Gives the media type without parameters, lower-case: "audio/webm;codecs=opus" is webm."""
    return (content_type or "").split(";", maxsplit=1)[0].strip().lower()


@dataclass(frozen=True, slots=True)
class SpeechLimits:
    """The largest recording accepted, in bytes (SPEECH_UPLOAD_MAX_BYTES)."""

    maximum_upload_bytes: int


class CustomerSpeechService:
    """Transcribes a session's recording and speaks a session's shown explanation."""

    def __init__(  # noqa: PLR0913 - one parameter per collaborator
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        sale_expiry: SaleExpiryStep,
        speech: SpeechPort | None,
        shown_explanation_cache: ShownExplanationCache,
        usage_logger: AiUsageLogger,
        model_names: SpeechModelNames,
        limits: SpeechLimits,
    ) -> None:
        """Keeps the session check, the speech port (None when off), the cache and the logger."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._session_access = CustomerSessionAccess(sale_expiry)
        self._speech = speech
        self._shown_explanation_cache = shown_explanation_cache
        self._usage_logger = usage_logger
        self._model_names = model_names
        self._limits = limits
        self._amount_parser = SpokenAmountParser()

    def check_upload_size(self, declared_size_in_bytes: int) -> None:
        """Refuses a recording over the limit, so an oversized body need not be read at all."""
        if declared_size_in_bytes > self._limits.maximum_upload_bytes:
            raise AudioTooLargeError("The recording is larger than the upload limit.")

    def transcribe_for_session(
        self,
        credentials: CustomerSessionCredentials,
        audio_content: bytes,
        content_type: str | None,
        purpose: SpeechTranscriptionPurpose,
        language: CustomerLanguage,
    ) -> SpeechTranscriptionResult:
        """Gives the text and the one amount heard; the budget is never changed here."""
        self.check_upload_size(len(audio_content))
        media_type = read_base_media_type(content_type)
        if not audio_content or media_type not in ACCEPTED_AUDIO_MEDIA_TYPES:
            raise AudioFormatUnsupportedError(
                "Send one recording as audio/webm, ogg, mp4, mpeg or wav."
            )
        with self._unit_of_work_factory() as unit_of_work:
            opened = self._session_access.open_sale(unit_of_work, credentials, self._clock.now())
        speech = self._require_speech()
        transcript = self._transcribe(
            speech, SpeechAudio(audio_content, media_type), language, purpose, credentials
        )
        amount_in_paise = self._amount_parser.parse_amount_in_paise(transcript.transcript)
        return SpeechTranscriptionResult(
            transcript=transcript.transcript,
            recognised_amount_in_paise=amount_in_paise,
            is_likely_misheard=self._amount_parser.is_likely_misheard(
                amount_in_paise, opened.sale.price.to_paise()
            ),
        )

    def synthesise_shown_explanation(
        self, credentials: CustomerSessionCredentials, explanation_id: str
    ) -> SynthesisedAudio:
        """Speaks exactly the explanation text this session was shown under explanation_id."""
        with self._unit_of_work_factory() as unit_of_work:
            self._session_access.authenticate(unit_of_work, credentials, self._clock.now())
        shown = self._shown_explanation_cache.find_by_explanation_id(
            credentials.customer_session_id, explanation_id
        )
        if shown is None:
            raise ExplanationNotFoundError("No explanation with this id was shown to the session.")
        speech = self._require_speech()
        text = shown.explanation.text
        started_at = time.perf_counter()
        try:
            audio = speech.synthesise(text, shown.explanation.language)
        except (SpeechTextTooLongError, InvalidAiValueError) as error:
            self._record_synthesis(credentials, started_at, len(text), 0, error.code)
            raise SpeechUnavailableError("The explanation could not be spoken.") from error
        except SpeechUnavailableError as error:
            self._record_synthesis(credentials, started_at, len(text), 0, error.code)
            raise
        self._record_synthesis(
            credentials, started_at, len(text), len(audio.content), COMPLETED_OUTCOME
        )
        return audio

    def _require_speech(self) -> SpeechPort:
        """Gives the speech port; switched off answers as unavailable (the customer types)."""
        if self._speech is None:
            raise SpeechUnavailableError(SPEECH_OFF_DETAIL)
        return self._speech

    def _transcribe(
        self,
        speech: SpeechPort,
        audio: SpeechAudio,
        language: CustomerLanguage,
        purpose: SpeechTranscriptionPurpose,
        credentials: CustomerSessionCredentials,
    ) -> SpeechTranscript:
        """Calls speech-to-text and logs its usage; an unusable answer counts as unavailable."""
        started_at = time.perf_counter()
        flow = f"speech_transcription_{purpose.value.lower()}"
        try:
            transcript = speech.transcribe(audio, language)
        except (SpeechUnavailableError, InvalidAiValueError) as error:
            self._record_transcription(
                flow=flow,
                started_at=started_at,
                audio_seconds=0,
                transcript_characters=0,
                outcome=error.code,
                credentials=credentials,
            )
            if isinstance(error, SpeechUnavailableError):
                raise
            raise SpeechUnavailableError("The recording could not be transcribed.") from error
        duration = transcript.audio_duration_in_seconds
        self._record_transcription(
            flow=flow,
            started_at=started_at,
            audio_seconds=0 if duration is None else math.ceil(duration),
            transcript_characters=len(transcript.transcript),
            outcome=COMPLETED_OUTCOME,
            credentials=credentials,
        )
        return transcript

    def _record_transcription(  # noqa: PLR0913 - the fields of one usage line
        self,
        *,
        flow: str,
        started_at: float,
        audio_seconds: int,
        transcript_characters: int,
        outcome: str,
        credentials: CustomerSessionCredentials,
    ) -> None:
        """Logs one speech-to-text call: seconds of audio in, characters out; no transcript."""
        self._usage_logger.record_speech_to_text_call(
            AiCallUsage(
                flow=flow,
                model=self._model_names.speech_to_text,
                latency_ms=measure_elapsed_milliseconds(started_at),
                model_input_usage_count=audio_seconds,
                model_output_usage_count=transcript_characters,
                outcome=outcome,
                customer_session_id=credentials.customer_session_id,
            )
        )

    def _record_synthesis(
        self,
        credentials: CustomerSessionCredentials,
        started_at: float,
        text_characters: int,
        audio_bytes: int,
        outcome: str,
    ) -> None:
        """Logs one text-to-speech call: characters in, audio bytes out; no text or audio."""
        self._usage_logger.record_text_to_speech_call(
            AiCallUsage(
                flow="speech_synthesis",
                model=self._model_names.text_to_speech,
                latency_ms=measure_elapsed_milliseconds(started_at),
                model_input_usage_count=text_characters,
                model_output_usage_count=audio_bytes,
                outcome=outcome,
                customer_session_id=credentials.customer_session_id,
            )
        )
