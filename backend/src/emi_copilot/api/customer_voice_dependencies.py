"""Providers of the customer voice and teach-back services (Layer 4, C2, C7 and C8).

Kept apart from customer_dependencies.py and ai_dependencies.py so neither grows past its size
limit; the speech port itself is built only by the composition root, through the AI factory.
"""

from typing import Annotated

from fastapi import Depends

from emi_copilot.api.ai_dependencies import AiUsageLoggerDependency, ShownExplanationCacheDependency
from emi_copilot.api.customer_dependencies import SessionPlanFinderDependency
from emi_copilot.api.dependencies import (
    ClockDependency,
    ComponentsDependency,
    UnitOfWorkFactoryDependency,
)
from emi_copilot.api.sale_dependencies import SaleExpiryDependency
from emi_copilot.config.ai_settings import AiProviderMode
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.services.ai.teach_back_feedback import TeachBackFeedbackWriter
from emi_copilot.services.ai.teach_back_flow import TeachBackFlow
from emi_copilot.services.customer.customer_speech_service import (
    CustomerSpeechService,
    SpeechLimits,
    SpeechModelNames,
)
from emi_copilot.services.customer.customer_teach_back_service import CustomerTeachBackService

MOCK_SPEECH_MODEL_NAMES = SpeechModelNames(
    speech_to_text="mock-speech-to-text", text_to_speech="mock-text-to-speech"
)


def provide_is_voice_available(components: ComponentsDependency) -> bool:
    """Tells the customer app whether to show the microphone: speech is not switched off."""
    return components.ai.speech is not None


def provide_customer_speech_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    components: ComponentsDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    sale_expiry: SaleExpiryDependency,
    shown_explanation_cache: ShownExplanationCacheDependency,
    usage_logger: AiUsageLoggerDependency,
) -> CustomerSpeechService:
    """Assembles transcription and synthesis on the configured speech port (None when off)."""
    settings = components.ai.settings
    is_sarvam = settings.speech_provider_mode is AiProviderMode.SARVAM
    return CustomerSpeechService(
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        sale_expiry=sale_expiry,
        speech=components.ai.speech,
        shown_explanation_cache=shown_explanation_cache,
        usage_logger=usage_logger,
        model_names=(
            SpeechModelNames(
                settings.sarvam_speech_to_text_model, settings.sarvam_text_to_speech_model
            )
            if is_sarvam
            else MOCK_SPEECH_MODEL_NAMES
        ),
        limits=SpeechLimits(settings.speech_upload_max_bytes),
    )


def provide_customer_teach_back_service(
    components: ComponentsDependency, plan_finder: SessionPlanFinderDependency
) -> CustomerTeachBackService:
    """Assembles the deterministic teach-back check on the configured flow runner."""
    return CustomerTeachBackService(
        plan_finder,
        TeachBackFlow(
            components.ai.flow_runner, TeachBackFeedbackWriter(format_paise_as_whole_rupees)
        ),
    )


IsVoiceAvailableDependency = Annotated[bool, Depends(provide_is_voice_available)]
CustomerSpeechServiceDependency = Annotated[
    CustomerSpeechService, Depends(provide_customer_speech_service)
]
CustomerTeachBackServiceDependency = Annotated[
    CustomerTeachBackService, Depends(provide_customer_teach_back_service)
]
