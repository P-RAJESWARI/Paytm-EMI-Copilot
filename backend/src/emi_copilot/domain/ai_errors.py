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
