"""AiProviderFactory: the one place that turns AI configuration into speech and text adapters.

Only the composition root (api/dependencies.py) imports this module (ADR 0008); services see
the ports in AiComponents and never a concrete adapter.
"""

import logging
from dataclasses import dataclass
from typing import NoReturn

from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.mock_explanation_text_adapter import MockExplanationTextAdapter
from emi_copilot.adapters.ai.mock_speech_adapter import MockSpeechAdapter
from emi_copilot.adapters.ai.speech_port import SpeechPort
from emi_copilot.config.ai_settings import AiProviderMode, AiSettings
from emi_copilot.domain.ai_errors import AiConfigurationError

SPEECH_MODE_VARIABLE = "SPEECH_PROVIDER_MODE"
EXPLANATION_TEXT_MODE_VARIABLE = "EXPLANATION_TEXT_PROVIDER_MODE"
PROVIDER_OFF_MESSAGE_TEMPLATE = "%s=off: this AI capability is switched off; templates are used"

ai_factory_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AiComponents:
    """The AI ports the application uses; a port switched off is None (the key stays hidden)."""

    speech: SpeechPort | None
    explanation_text: ExplanationTextPort | None
    settings: AiSettings


def refuse_unavailable_sarvam_mode(settings: AiSettings, mode_variable: str) -> NoReturn:
    """Fails startup for Sarvam mode: without SARVAM_API_KEY, or before its adapter exists."""
    if settings.sarvam_api_key is None:
        raise AiConfigurationError(
            f"{mode_variable}=sarvam needs SARVAM_API_KEY; refusing to start (ADR 0004 style)."
        )
    raise AiConfigurationError(f"{mode_variable}=sarvam is not available in this build yet.")


def announce_provider_off(mode_variable: str) -> None:
    """Logs at startup that a capability is off, so nobody expects voice or AI text."""
    ai_factory_logger.warning(PROVIDER_OFF_MESSAGE_TEMPLATE, mode_variable)


# Pattern: Factory. Chooses off, the labelled Mock or Sarvam per AI capability in one place, and
# refuses Sarvam mode without its key instead of falling back (ADR 0004 style). Each Mock
# announces itself as it is built; "off" is announced here.
class AiProviderFactory:
    """Builds AiComponents for SPEECH_PROVIDER_MODE and EXPLANATION_TEXT_PROVIDER_MODE."""

    def create(self, settings: AiSettings) -> AiComponents:
        """Builds both configured ports; raises AiConfigurationError for an unusable mode."""
        return AiComponents(
            speech=self._create_speech(settings),
            explanation_text=self._create_explanation_text(settings),
            settings=settings,
        )

    def _create_speech(self, settings: AiSettings) -> SpeechPort | None:
        """Builds the speech port for its mode; None when speech is off."""
        if settings.speech_provider_mode is AiProviderMode.SARVAM:
            refuse_unavailable_sarvam_mode(settings, SPEECH_MODE_VARIABLE)
        if settings.speech_provider_mode is AiProviderMode.OFF:
            announce_provider_off(SPEECH_MODE_VARIABLE)
            return None
        return MockSpeechAdapter()

    def _create_explanation_text(self, settings: AiSettings) -> ExplanationTextPort | None:
        """Builds the explanation text port for its mode; None when AI text is off."""
        if settings.explanation_text_provider_mode is AiProviderMode.SARVAM:
            refuse_unavailable_sarvam_mode(settings, EXPLANATION_TEXT_MODE_VARIABLE)
        if settings.explanation_text_provider_mode is AiProviderMode.OFF:
            announce_provider_off(EXPLANATION_TEXT_MODE_VARIABLE)
            return None
        return MockExplanationTextAdapter(settings.mock_ai_text_behaviour)
