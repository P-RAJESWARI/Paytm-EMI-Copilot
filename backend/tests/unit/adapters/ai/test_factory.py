"""AiProviderFactory builds labelled Mocks by default, honours off, refuses Sarvam without key."""

import logging

import pytest
from pydantic import SecretStr

from emi_copilot.adapters.ai.factory import AiProviderFactory
from emi_copilot.adapters.ai.mock_explanation_text_adapter import MockExplanationTextAdapter
from emi_copilot.adapters.ai.mock_speech_adapter import (
    MOCK_SPEECH_ACTIVE_WARNING,
    MockSpeechAdapter,
)
from emi_copilot.adapters.ai.sarvam.sarvam_speech_adapter import SarvamSpeechAdapter
from emi_copilot.config.ai_settings import AiProviderMode, AiSettings
from emi_copilot.core.clock import SystemClock
from emi_copilot.domain.ai_errors import AiConfigurationError

SYNTHETIC_SARVAM_KEY = "synthetic-sarvam-key-for-tests"  # pragma: allowlist secret
CLOCK = SystemClock()


def test_ai_factory_default_settings_build_both_mocks_and_announce_them(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Rule 10: Mocks are the default and each one is named in the startup log."""
    settings = AiSettings()
    with caplog.at_level(logging.WARNING):
        components = AiProviderFactory().create(settings, CLOCK)
    assert isinstance(components.speech, MockSpeechAdapter)
    assert isinstance(components.explanation_text, MockExplanationTextAdapter)
    assert components.settings is settings
    messages = [record.getMessage() for record in caplog.records]
    assert MOCK_SPEECH_ACTIVE_WARNING in messages
    assert any("MockExplanationTextAdapter active" in message for message in messages)


def test_ai_factory_off_mode_gives_no_ports_and_announces_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With AI off every screen uses templates and no Mock is built."""
    settings = AiSettings(
        speech_provider_mode=AiProviderMode.OFF,
        explanation_text_provider_mode=AiProviderMode.OFF,
    )
    with caplog.at_level(logging.WARNING):
        components = AiProviderFactory().create(settings, CLOCK)
    assert components.speech is None
    assert components.explanation_text is None
    off_suffix = "=off: this AI capability is switched off; templates are used"
    assert [record.getMessage() for record in caplog.records] == [
        f"SPEECH_PROVIDER_MODE{off_suffix}",
        f"EXPLANATION_TEXT_PROVIDER_MODE{off_suffix}",
    ]


@pytest.mark.parametrize(
    ("settings_fields", "expected_variable"),
    [
        ({"speech_provider_mode": AiProviderMode.SARVAM}, "SPEECH_PROVIDER_MODE"),
        (
            {"explanation_text_provider_mode": AiProviderMode.SARVAM},
            "EXPLANATION_TEXT_PROVIDER_MODE",
        ),
    ],
)
def test_ai_factory_sarvam_mode_without_key_refuses_to_start(
    settings_fields: dict[str, AiProviderMode], expected_variable: str
) -> None:
    """Sarvam mode never falls back to a Mock: startup fails naming the missing variable."""
    with pytest.raises(
        AiConfigurationError, match=f"{expected_variable}=sarvam needs SARVAM_API_KEY"
    ):
        AiProviderFactory().create(AiSettings.model_validate(settings_fields), CLOCK)


def test_ai_factory_sarvam_mode_with_key_refuses_until_the_adapter_exists() -> None:
    """Until the Sarvam adapters are built, a configured key still cannot start Sarvam mode."""
    settings = AiSettings(
        explanation_text_provider_mode=AiProviderMode.SARVAM,
        sarvam_api_key=SecretStr(SYNTHETIC_SARVAM_KEY),
    )
    with pytest.raises(AiConfigurationError, match="not available in this build yet") as raised:
        AiProviderFactory().create(settings, CLOCK)
    assert SYNTHETIC_SARVAM_KEY not in str(raised.value)


def test_ai_factory_speech_in_sarvam_mode_with_key_builds_the_sarvam_adapter(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a key, speech is real and announced by host; the key is never logged."""
    settings = AiSettings(
        speech_provider_mode=AiProviderMode.SARVAM, sarvam_api_key=SecretStr(SYNTHETIC_SARVAM_KEY)
    )
    with caplog.at_level(logging.INFO):
        components = AiProviderFactory().create(settings, CLOCK)
    assert isinstance(components.speech, SarvamSpeechAdapter)
    assert "SarvamSpeechAdapter active" in caplog.text
    assert SYNTHETIC_SARVAM_KEY not in caplog.text
