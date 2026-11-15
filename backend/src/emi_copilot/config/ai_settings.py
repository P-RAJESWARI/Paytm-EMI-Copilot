"""Typed settings of the AI components (Layer 4), read from environment variables.

Kept apart from settings.py, which is already long; ApplicationSettings holds one AiSettings.
Prices are rates, not amounts, so they are Decimal parsed from strings and never floats.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SARVAM_DEFAULT_BASE_URL = "https://api.sarvam.ai"
# [Verify] "shubh" is a documented bulbul:v3 speaker; confirm it reads Tamil and English well.
SARVAM_DEFAULT_SPEAKER = "shubh"

ChatReasoningEffort = Literal["low", "medium", "high"]


class AiProviderMode(StrEnum):
    """Which implementation an AI port gets: none at all, the labelled Mock, or Sarvam."""

    OFF = "off"
    MOCK = "mock"
    SARVAM = "sarvam"


class AiFlowRunnerChoice(StrEnum):
    """Which runner executes the AI flows: plain Python, or the optional LangGraph extra."""

    SEQUENTIAL = "sequential"
    LANGGRAPH = "langgraph"


class MockAiTextBehaviour(StrEnum):
    """How the Mock explanation text adapter behaves, so tests and the demo can show fallback."""

    CORRECT = "correct"
    WRONG_NUMBER = "wrong_number"
    UNAVAILABLE = "unavailable"


class AiSettings(BaseSettings):
    """All AI configuration, one typed field per environment variable; Mocks are the default."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore", frozen=True)

    speech_provider_mode: AiProviderMode = AiProviderMode.MOCK
    explanation_text_provider_mode: AiProviderMode = AiProviderMode.MOCK
    ai_flow_runner: AiFlowRunnerChoice = AiFlowRunnerChoice.SEQUENTIAL
    mock_ai_text_behaviour: MockAiTextBehaviour = MockAiTextBehaviour.CORRECT
    # Sarvam mode refuses to start without the key; it is never logged (ADR 0004 style).
    sarvam_api_key: SecretStr | None = None
    sarvam_base_url: str = SARVAM_DEFAULT_BASE_URL
    # One timeout and breaker per capability, so a slow chat model cannot trip speech. Calls are
    # not retried: they cost credits and every caller has a fallback.
    sarvam_speech_to_text_connect_timeout_in_seconds: float = Field(default=3.0, gt=0)
    sarvam_speech_to_text_read_timeout_in_seconds: float = Field(default=10.0, gt=0)
    sarvam_speech_to_text_circuit_breaker_failure_threshold: int = Field(default=3, ge=1)
    sarvam_speech_to_text_circuit_breaker_open_duration_in_seconds: float = Field(
        default=30.0, gt=0
    )
    sarvam_text_to_speech_connect_timeout_in_seconds: float = Field(default=3.0, gt=0)
    sarvam_text_to_speech_read_timeout_in_seconds: float = Field(default=10.0, gt=0)
    sarvam_text_to_speech_circuit_breaker_failure_threshold: int = Field(default=3, ge=1)
    sarvam_text_to_speech_circuit_breaker_open_duration_in_seconds: float = Field(
        default=30.0, gt=0
    )
    # sarvam-105b answers in 3 to 8 s; after 6 s the template text is shown instead.
    sarvam_chat_connect_timeout_in_seconds: float = Field(default=3.0, gt=0)
    sarvam_chat_read_timeout_in_seconds: float = Field(default=6.0, gt=0)
    sarvam_chat_circuit_breaker_failure_threshold: int = Field(default=3, ge=1)
    sarvam_chat_circuit_breaker_open_duration_in_seconds: float = Field(default=30.0, gt=0)
    sarvam_speech_to_text_model: str = Field(default="saaras:v4", min_length=1)
    sarvam_text_to_speech_model: str = Field(default="bulbul:v3", min_length=1)
    sarvam_chat_model: str = Field(default="sarvam-105b", min_length=1)
    sarvam_text_to_speech_english_speaker: str = Field(default=SARVAM_DEFAULT_SPEAKER, min_length=1)
    sarvam_text_to_speech_tamil_speaker: str = Field(default=SARVAM_DEFAULT_SPEAKER, min_length=1)
    sarvam_chat_temperature: Decimal = Field(default=Decimal("0.2"), ge=0, le=2)
    sarvam_chat_max_tokens: int = Field(default=600, ge=1, le=4_000)
    # [Verify] whether sarvam-105b accepts reasoning_effort and counts it within max_tokens.
    sarvam_chat_reasoning_effort: ChatReasoningEffort = "low"
    # [Verify] Sarvam's published prices (checked 15 Nov 2026), in rupees; used for cost estimates.
    sarvam_speech_to_text_price_in_rupees_per_minute: Decimal = Field(default=Decimal("0.49"), ge=0)
    sarvam_text_to_speech_price_in_rupees_per_thousand_characters: Decimal = Field(
        default=Decimal("3.00"), ge=0
    )
    sarvam_chat_input_price_in_rupees_per_million_tokens: Decimal = Field(
        default=Decimal("15"), ge=0
    )
    sarvam_chat_output_price_in_rupees_per_million_tokens: Decimal = Field(
        default=Decimal("60"), ge=0
    )
    # Demo limits (plan Q13): one recording is at most 512 KiB and 15 s, and one customer
    # session may make this many AI calls per window (in memory, per process).
    speech_upload_max_bytes: int = Field(default=524_288, ge=1_024, le=5_242_880)
    speech_max_recording_seconds: int = Field(default=15, ge=1, le=29)
    ai_session_rate_limit_max_requests: int = Field(default=10, ge=1)
    ai_session_rate_limit_window_in_seconds: int = Field(default=60, ge=1)

    @field_validator("sarvam_api_key", mode="before")
    @classmethod
    def treat_blank_key_as_unset(cls, value: object) -> object:
        """Reads an empty or blank SARVAM_API_KEY, as copied from .env.example, as not set."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "sarvam_chat_temperature",
        "sarvam_speech_to_text_price_in_rupees_per_minute",
        "sarvam_text_to_speech_price_in_rupees_per_thousand_characters",
        "sarvam_chat_input_price_in_rupees_per_million_tokens",
        "sarvam_chat_output_price_in_rupees_per_million_tokens",
        mode="before",
    )
    @classmethod
    def refuse_float_for_decimal_value(cls, value: object) -> object:
        """Rejects a float, which cannot hold 0.49 exactly; a string or Decimal is required."""
        if isinstance(value, float):
            raise ValueError("give this value as a string or Decimal, never a float")  # noqa: TRY004
        return value

    @field_validator("sarvam_base_url")
    @classmethod
    def check_sarvam_base_url(cls, value: str) -> str:
        """Accepts an https origin without query or fragment, so keys only travel over TLS."""
        parts = urlsplit(value)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError("SARVAM_BASE_URL must be an https URL with a host")
        if parts.query or parts.fragment:
            raise ValueError("SARVAM_BASE_URL must not have a query or a fragment")
        return value.rstrip("/")
