"""Typed errors of the AI components (Layer 4): speech, explanation text and their configuration.

Kept apart from domain/errors.py, which is already over the soft file limit. Messages are
English, developer-facing and never contain customer speech, AI text, keys or vendor payloads.
"""

from typing import ClassVar

from emi_copilot.domain.errors import DomainError


class AiConfigurationError(DomainError):
    """Raised at startup when an AI provider mode cannot be built as configured (ADR 0004 style).

    The message names the missing or unusable setting, never its value.
    """

    code: ClassVar[str] = "AI_CONFIGURATION_INVALID"


class InvalidAiValueError(DomainError):
    """Raised when a value passed to or returned by an AI port is empty or malformed."""

    code: ClassVar[str] = "INVALID_AI_VALUE"


class AiProviderError(DomainError):
    """Base class for an AI provider call that gave no usable result; callers fall back."""

    code: ClassVar[str] = "AI_PROVIDER_FAILED"


class AiTextUnavailableError(AiProviderError):
    """Raised when no explanation text could be written, so the template text is shown instead."""

    code: ClassVar[str] = "AI_TEXT_UNAVAILABLE"


class SpeechUnavailableError(AiProviderError):
    """Raised when speech could not be transcribed or synthesised; the customer types instead."""

    code: ClassVar[str] = "SPEECH_UNAVAILABLE"


class SpeechTimeoutError(SpeechUnavailableError):
    """Raised when the speech provider did not answer within its configured timeout."""

    code: ClassVar[str] = "SPEECH_TIMEOUT"


class SpeechTextTooLongError(SpeechUnavailableError):
    """Raised before sending when text is longer than text-to-speech accepts; no credit is spent."""

    code: ClassVar[str] = "SPEECH_TEXT_TOO_LONG"


class InvalidAiFlowError(DomainError):
    """Raised when a flow definition has no steps, repeated step names or too many steps."""

    code: ClassVar[str] = "INVALID_AI_FLOW"


class InvalidTeachBackInputError(DomainError):
    """Raised when a teach-back tolerance is not a Decimal share from 0 up to 1."""

    code: ClassVar[str] = "INVALID_TEACH_BACK_INPUT"


class AudioTooLargeError(DomainError):
    """Raised when an uploaded recording is larger than SPEECH_UPLOAD_MAX_BYTES allows."""

    code: ClassVar[str] = "AUDIO_TOO_LARGE"


class AudioFormatUnsupportedError(DomainError):
    """Raised when an upload is empty or not one of the accepted audio media types."""

    code: ClassVar[str] = "AUDIO_FORMAT_UNSUPPORTED"


class ExplanationNotFoundError(DomainError):
    """Raised when no explanation with this id was shown to this session (or it has expired)."""

    code: ClassVar[str] = "EXPLANATION_NOT_FOUND"
