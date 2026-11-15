"""The composition root builds the AI components once at startup and fails fast in sarvam mode."""

import logging

import pytest
from fastapi.testclient import TestClient

from emi_copilot.adapters.ai.mock_explanation_text_adapter import MockExplanationTextAdapter
from emi_copilot.adapters.ai.mock_speech_adapter import MockSpeechAdapter
from emi_copilot.config.ai_settings import AiProviderMode, AiSettings
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.domain.ai_errors import AiConfigurationError
from emi_copilot.main import create_application


def test_startup_with_default_settings_builds_the_labelled_ai_mocks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Both AI ports are Mocks by default, kept on app.state and named in the startup log."""
    application = create_application(ApplicationSettings())
    with caplog.at_level(logging.WARNING), TestClient(application):
        ai_components = application.state.application_components.ai
        assert isinstance(ai_components.speech, MockSpeechAdapter)
        assert isinstance(ai_components.explanation_text, MockExplanationTextAdapter)
    announced_messages = " ".join(record.getMessage() for record in caplog.records)
    assert "MockSpeechAdapter active" in announced_messages
    assert "MockExplanationTextAdapter active" in announced_messages


def test_startup_with_speech_in_sarvam_mode_without_key_fails() -> None:
    """Sarvam mode never falls back to the Mock: startup itself raises."""
    application = create_application(
        ApplicationSettings(ai_settings=AiSettings(speech_provider_mode=AiProviderMode.SARVAM))
    )
    with (
        pytest.raises(AiConfigurationError, match="SARVAM_API_KEY"),
        TestClient(application),
    ):
        pass
