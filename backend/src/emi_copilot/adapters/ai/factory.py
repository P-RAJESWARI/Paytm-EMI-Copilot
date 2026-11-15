"""AiProviderFactory: the one place that turns AI configuration into speech, text and flows.

Only the composition root (api/dependencies.py) imports this module (ADR 0008); services see
the ports in AiComponents and never a concrete adapter.
"""

import logging
from dataclasses import dataclass

from pydantic import SecretStr

from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.flows.flow_runner_builder import build_flow_runner
from emi_copilot.adapters.ai.flows.flow_runner_port import AiFlowRunnerPort
from emi_copilot.adapters.ai.mock_explanation_text_adapter import MockExplanationTextAdapter
from emi_copilot.adapters.ai.mock_speech_adapter import MockSpeechAdapter
from emi_copilot.adapters.ai.sarvam.sarvam_adapter_builder import (
    build_sarvam_chat_text_adapter,
    build_sarvam_speech_adapter,
)
from emi_copilot.adapters.ai.speech_port import SpeechPort
from emi_copilot.config.ai_settings import AiProviderMode, AiSettings
from emi_copilot.core.clock import Clock
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
    flow_runner: AiFlowRunnerPort
    settings: AiSettings


def require_sarvam_api_key(settings: AiSettings, mode_variable: str) -> SecretStr:
    """Gives the key Sarvam mode needs, or fails startup naming the missing variable."""
    if settings.sarvam_api_key is None:
        raise AiConfigurationError(
            f"{mode_variable}=sarvam needs SARVAM_API_KEY; refusing to start (ADR 0004 style)."
        )
    return settings.sarvam_api_key


def announce_provider_off(mode_variable: str) -> None:
    """Logs at startup that a capability is off, so nobody expects voice or AI text."""
    ai_factory_logger.warning(PROVIDER_OFF_MESSAGE_TEMPLATE, mode_variable)


# Pattern: Factory. Chooses off, the labelled Mock or Sarvam per AI capability in one place, and
# refuses Sarvam mode without its key instead of falling back (ADR 0004 style). Each Mock
# announces itself as it is built; "off" is announced here.
class AiProviderFactory:
    """Builds AiComponents for the two provider modes and AI_FLOW_RUNNER."""

    def create(self, settings: AiSettings, clock: Clock) -> AiComponents:
        """Builds both configured ports; raises AiConfigurationError for an unusable mode."""
        return AiComponents(
            speech=self._create_speech(settings, clock),
            explanation_text=self._create_explanation_text(settings, clock),
            flow_runner=build_flow_runner(settings.ai_flow_runner),
            settings=settings,
        )

    def _create_speech(self, settings: AiSettings, clock: Clock) -> SpeechPort | None:
        """Builds the speech port for its mode; None when speech is off."""
        if settings.speech_provider_mode is AiProviderMode.SARVAM:
            api_key = require_sarvam_api_key(settings, SPEECH_MODE_VARIABLE)
            return build_sarvam_speech_adapter(settings, api_key, clock)
        if settings.speech_provider_mode is AiProviderMode.OFF:
            announce_provider_off(SPEECH_MODE_VARIABLE)
            return None
        return MockSpeechAdapter()

    def _create_explanation_text(
        self, settings: AiSettings, clock: Clock
    ) -> ExplanationTextPort | None:
        """Builds the explanation text port for its mode; None when AI text is off."""
        if settings.explanation_text_provider_mode is AiProviderMode.SARVAM:
            api_key = require_sarvam_api_key(settings, EXPLANATION_TEXT_MODE_VARIABLE)
            return build_sarvam_chat_text_adapter(settings, api_key, clock)
        if settings.explanation_text_provider_mode is AiProviderMode.OFF:
            announce_provider_off(EXPLANATION_TEXT_MODE_VARIABLE)
            return None
        return MockExplanationTextAdapter(settings.mock_ai_text_behaviour)
