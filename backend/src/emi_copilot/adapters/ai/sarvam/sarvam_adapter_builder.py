"""Builds the Sarvam adapters from AiSettings; used only by AiProviderFactory."""

import logging
from urllib.parse import urlsplit

from pydantic import SecretStr

from emi_copilot.adapters.ai.sarvam.sarvam_api_definitions import (
    CHAT_DEPENDENCY_NAME,
    SPEECH_TO_TEXT_DEPENDENCY_NAME,
    TEXT_TO_SPEECH_DEPENDENCY_NAME,
)
from emi_copilot.adapters.ai.sarvam.sarvam_chat_text_adapter import SarvamChatTextAdapter
from emi_copilot.adapters.ai.sarvam.sarvam_http_clients import (
    SarvamCallLimits,
    build_sarvam_http_client,
)
from emi_copilot.adapters.ai.sarvam.sarvam_speech_adapter import (
    SarvamSpeechAdapter,
    SarvamSpeechHttpClients,
)
from emi_copilot.config.ai_settings import AiSettings
from emi_copilot.core.clock import Clock

SARVAM_SPEECH_ACTIVE_MESSAGE = "SarvamSpeechAdapter active: real Sarvam speech calls are made"
SARVAM_CHAT_ACTIVE_MESSAGE = "SarvamChatTextAdapter active: real Sarvam chat calls are made"

sarvam_adapter_builder_logger = logging.getLogger(__name__)


def speech_to_text_limits(settings: AiSettings) -> SarvamCallLimits:
    """Gives the speech-to-text timeouts and breaker settings."""
    return SarvamCallLimits(
        dependency_name=SPEECH_TO_TEXT_DEPENDENCY_NAME,
        connect_timeout_in_seconds=settings.sarvam_speech_to_text_connect_timeout_in_seconds,
        read_timeout_in_seconds=settings.sarvam_speech_to_text_read_timeout_in_seconds,
        circuit_breaker_failure_threshold=settings.sarvam_speech_to_text_circuit_breaker_failure_threshold,
        circuit_breaker_open_duration_in_seconds=settings.sarvam_speech_to_text_circuit_breaker_open_duration_in_seconds,
    )


def text_to_speech_limits(settings: AiSettings) -> SarvamCallLimits:
    """Gives the text-to-speech timeouts and breaker settings."""
    return SarvamCallLimits(
        dependency_name=TEXT_TO_SPEECH_DEPENDENCY_NAME,
        connect_timeout_in_seconds=settings.sarvam_text_to_speech_connect_timeout_in_seconds,
        read_timeout_in_seconds=settings.sarvam_text_to_speech_read_timeout_in_seconds,
        circuit_breaker_failure_threshold=settings.sarvam_text_to_speech_circuit_breaker_failure_threshold,
        circuit_breaker_open_duration_in_seconds=settings.sarvam_text_to_speech_circuit_breaker_open_duration_in_seconds,
    )


def chat_limits(settings: AiSettings) -> SarvamCallLimits:
    """Gives the chat timeouts (6 s read by default) and breaker settings."""
    return SarvamCallLimits(
        dependency_name=CHAT_DEPENDENCY_NAME,
        connect_timeout_in_seconds=settings.sarvam_chat_connect_timeout_in_seconds,
        read_timeout_in_seconds=settings.sarvam_chat_read_timeout_in_seconds,
        circuit_breaker_failure_threshold=settings.sarvam_chat_circuit_breaker_failure_threshold,
        circuit_breaker_open_duration_in_seconds=settings.sarvam_chat_circuit_breaker_open_duration_in_seconds,
    )


def announce_sarvam_adapter(message: str, settings: AiSettings) -> None:
    """Announces a real Sarvam adapter with its host only; never the key."""
    sarvam_adapter_builder_logger.info(
        message, extra={"sarvam_host": urlsplit(settings.sarvam_base_url).netloc}
    )


def build_sarvam_speech_adapter(
    settings: AiSettings, api_key: SecretStr, clock: Clock
) -> SarvamSpeechAdapter:
    """Builds the speech adapter with one client and breaker per capability, and announces it."""
    adapter = SarvamSpeechAdapter(
        settings,
        api_key,
        SarvamSpeechHttpClients(
            speech_to_text=build_sarvam_http_client(speech_to_text_limits(settings), clock),
            text_to_speech=build_sarvam_http_client(text_to_speech_limits(settings), clock),
        ),
    )
    announce_sarvam_adapter(SARVAM_SPEECH_ACTIVE_MESSAGE, settings)
    return adapter


def build_sarvam_chat_text_adapter(
    settings: AiSettings, api_key: SecretStr, clock: Clock
) -> SarvamChatTextAdapter:
    """Builds the chat adapter with its own client and breaker, and announces it."""
    adapter = SarvamChatTextAdapter(
        settings, api_key, build_sarvam_http_client(chat_limits(settings), clock)
    )
    announce_sarvam_adapter(SARVAM_CHAT_ACTIVE_MESSAGE, settings)
    return adapter
