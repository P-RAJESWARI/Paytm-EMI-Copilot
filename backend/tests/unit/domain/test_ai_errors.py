"""AI errors are typed domain errors with stable codes; provider failures share one base."""

import pytest

from emi_copilot.domain.ai_errors import (
    AiConfigurationError,
    AiProviderError,
    AiTextUnavailableError,
    InvalidAiValueError,
    SpeechTimeoutError,
    SpeechUnavailableError,
)
from emi_copilot.domain.errors import DomainError


@pytest.mark.parametrize(
    ("error_class", "expected_code"),
    [
        (AiConfigurationError, "AI_CONFIGURATION_INVALID"),
        (InvalidAiValueError, "INVALID_AI_VALUE"),
        (AiProviderError, "AI_PROVIDER_FAILED"),
        (AiTextUnavailableError, "AI_TEXT_UNAVAILABLE"),
        (SpeechUnavailableError, "SPEECH_UNAVAILABLE"),
        (SpeechTimeoutError, "SPEECH_TIMEOUT"),
    ],
)
def test_ai_error_is_a_domain_error_with_its_stable_code(
    error_class: type[DomainError], expected_code: str
) -> None:
    """Each AI error keeps its detail and maps to a fixed machine-readable code."""
    error = error_class("synthetic detail")
    assert isinstance(error, DomainError)
    assert error.code == expected_code
    assert error.detail == "synthetic detail"


@pytest.mark.parametrize(
    "error_class", [AiTextUnavailableError, SpeechUnavailableError, SpeechTimeoutError]
)
def test_ai_provider_failures_share_one_base_so_callers_can_fall_back(
    error_class: type[AiProviderError],
) -> None:
    """The audited services catch AiProviderError once to fall back to the template."""
    assert issubclass(error_class, AiProviderError)


def test_speech_timeout_is_a_kind_of_speech_unavailable() -> None:
    """A timeout is handled like any other speech outage unless a caller asks for it."""
    assert issubclass(SpeechTimeoutError, SpeechUnavailableError)
