"""AiSettings: Mocks by default, Decimal prices from strings, and unusable values refused."""

import re
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from emi_copilot.config.ai_settings import (
    AiFlowRunnerChoice,
    AiProviderMode,
    AiSettings,
    MockAiTextBehaviour,
)
from emi_copilot.config.settings import ApplicationSettings

ENVIRONMENT_EXAMPLE_FILE = Path(__file__).resolve().parents[4] / ".env.example"
SYNTHETIC_SARVAM_KEY = "synthetic-sarvam-key-for-tests"  # pragma: allowlist secret


def test_ai_settings_without_variables_use_mocks_and_the_documented_defaults() -> None:
    """Nothing set means labelled Mocks, the plain runner and the plan's demo limits."""
    settings = AiSettings()
    assert settings.speech_provider_mode is AiProviderMode.MOCK
    assert settings.explanation_text_provider_mode is AiProviderMode.MOCK
    assert settings.ai_flow_runner is AiFlowRunnerChoice.SEQUENTIAL
    assert settings.mock_ai_text_behaviour is MockAiTextBehaviour.CORRECT
    assert settings.sarvam_api_key is None
    assert settings.sarvam_base_url == "https://api.sarvam.ai"
    assert settings.sarvam_chat_read_timeout_in_seconds == 6.0
    assert (settings.sarvam_speech_to_text_model, settings.sarvam_text_to_speech_model) == (
        "saaras:v4",
        "bulbul:v3",
    )
    assert settings.sarvam_chat_model == "sarvam-105b-conversations"
    assert settings.sarvam_text_to_speech_tamil_speaker == "shubh"
    assert settings.sarvam_chat_temperature == Decimal("0.2")
    assert settings.sarvam_chat_reasoning_effort == "low"
    assert settings.speech_upload_max_bytes == 524_288
    assert settings.speech_max_recording_seconds == 15
    assert settings.ai_session_rate_limit_max_requests == 10
    assert settings.ai_session_rate_limit_window_in_seconds == 60


def test_ai_settings_prices_from_environment_strings_parse_as_exact_decimals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prices are rates in rupees, so they must stay exact: 0.49 is Decimal("0.49")."""
    monkeypatch.setenv("SARVAM_SPEECH_TO_TEXT_PRICE_IN_RUPEES_PER_MINUTE", "0.49")
    monkeypatch.setenv("SARVAM_TEXT_TO_SPEECH_PRICE_IN_RUPEES_PER_THOUSAND_CHARACTERS", "3.10")
    monkeypatch.setenv("SARVAM_CHAT_TEMPERATURE", "0.3")
    settings = AiSettings()
    assert settings.sarvam_speech_to_text_price_in_rupees_per_minute == Decimal("0.49")
    assert isinstance(settings.sarvam_speech_to_text_price_in_rupees_per_minute, Decimal)
    assert settings.sarvam_text_to_speech_price_in_rupees_per_thousand_characters == Decimal("3.10")
    assert settings.sarvam_chat_temperature == Decimal("0.3")
    assert settings.sarvam_chat_input_price_in_rupees_per_million_tokens == Decimal(15)
    assert settings.sarvam_chat_output_price_in_rupees_per_million_tokens == Decimal(60)


@pytest.mark.parametrize(
    "field_name",
    ["sarvam_chat_temperature", "sarvam_chat_output_price_in_rupees_per_million_tokens"],
)
def test_ai_settings_with_a_float_decimal_value_is_rejected(field_name: str) -> None:
    """A float cannot hold 0.49 exactly, so prices and the temperature refuse floats."""
    with pytest.raises(ValidationError, match="never a float"):
        AiSettings.model_validate({field_name: 0.49})


@pytest.mark.parametrize(
    ("variable_name", "variable_value"),
    [
        ("SPEECH_PROVIDER_MODE", "openai"),
        ("EXPLANATION_TEXT_PROVIDER_MODE", "on"),
        ("AI_FLOW_RUNNER", "langchain"),
        ("MOCK_AI_TEXT_BEHAVIOUR", "random"),
        ("SARVAM_CHAT_REASONING_EFFORT", "none"),
        ("SARVAM_CHAT_TEMPERATURE", "-0.1"),
        ("SARVAM_CHAT_INPUT_PRICE_IN_RUPEES_PER_MILLION_TOKENS", "-1"),
        ("SPEECH_MAX_RECORDING_SECONDS", "30"),
        ("SARVAM_CHAT_READ_TIMEOUT_IN_SECONDS", "0"),
    ],
)
def test_ai_settings_with_an_unknown_mode_or_out_of_range_value_is_rejected(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, variable_value: str
) -> None:
    """A typo in a mode or limit stops startup instead of silently using something else."""
    monkeypatch.setenv(variable_name, variable_value)
    with pytest.raises(ValidationError):
        AiSettings()


def test_ai_settings_modes_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each capability's mode is set on its own variable."""
    monkeypatch.setenv("SPEECH_PROVIDER_MODE", "off")
    monkeypatch.setenv("EXPLANATION_TEXT_PROVIDER_MODE", "sarvam")
    monkeypatch.setenv("AI_FLOW_RUNNER", "langgraph")
    monkeypatch.setenv("MOCK_AI_TEXT_BEHAVIOUR", "wrong_number")
    settings = AiSettings()
    assert settings.speech_provider_mode is AiProviderMode.OFF
    assert settings.explanation_text_provider_mode is AiProviderMode.SARVAM
    assert settings.ai_flow_runner is AiFlowRunnerChoice.LANGGRAPH
    assert settings.mock_ai_text_behaviour is MockAiTextBehaviour.WRONG_NUMBER


@pytest.mark.parametrize("blank_value", ["", "   "])
def test_ai_settings_with_a_blank_key_copied_from_env_example_means_not_set(
    monkeypatch: pytest.MonkeyPatch, blank_value: str
) -> None:
    """The empty placeholder in .env.example is "no key", never an empty secret."""
    monkeypatch.setenv("SARVAM_API_KEY", blank_value)
    assert AiSettings().sarvam_api_key is None


def test_ai_settings_key_is_a_secret_hidden_from_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """The key never appears when settings are printed or logged."""
    monkeypatch.setenv("SARVAM_API_KEY", SYNTHETIC_SARVAM_KEY)
    settings = AiSettings()
    assert isinstance(settings.sarvam_api_key, SecretStr)
    assert settings.sarvam_api_key.get_secret_value() == SYNTHETIC_SARVAM_KEY
    assert SYNTHETIC_SARVAM_KEY not in repr(settings)


def test_ai_settings_base_url_drops_a_final_slash() -> None:
    """Paths are joined onto the base URL later, so a trailing slash is removed."""
    assert AiSettings(sarvam_base_url="https://api.sarvam.ai/").sarvam_base_url == (
        "https://api.sarvam.ai"
    )


@pytest.mark.parametrize(
    "base_url",
    ["http://api.sarvam.ai", "https://", "https://api.sarvam.ai?debug=1", "https://a.test/#x"],
)
def test_ai_settings_base_url_without_tls_or_with_query_is_rejected(base_url: str) -> None:
    """The key travels in a header, so only plain https origins are accepted."""
    with pytest.raises(ValidationError, match="SARVAM_BASE_URL"):
        AiSettings(sarvam_base_url=base_url)


def test_application_settings_hold_ai_settings_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The composition root reaches AI configuration through the one settings object."""
    monkeypatch.setenv("SPEECH_PROVIDER_MODE", "off")
    assert ApplicationSettings().ai_settings.speech_provider_mode is AiProviderMode.OFF


def test_env_example_lists_every_ai_variable_without_a_key_value() -> None:
    """Every AI setting is documented with a placeholder, and the key placeholder is empty."""
    example_text = ENVIRONMENT_EXAMPLE_FILE.read_text(encoding="utf-8")
    for field_name in AiSettings.model_fields:
        assert re.search(rf"^{field_name.upper()}=", example_text, re.MULTILINE), field_name
    assert re.search(r"^SARVAM_API_KEY=$", example_text, re.MULTILINE)
