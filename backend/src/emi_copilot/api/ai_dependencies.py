"""Providers of the AI-backed services (Layer 4), assembled per request from startup components.

Kept beside dependencies.py (the composition root), which builds the AI ports through the
factory; this module only hands those ports, the shared caches and the prices to services.
"""

from typing import Annotated

from fastapi import Depends

from emi_copilot.api.dependencies import ComponentsDependency
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageTemplate
from emi_copilot.services.ai.ai_usage_logger import AiPriceList, AiUsageLogger
from emi_copilot.services.ai.audited_explanation_service import AuditedExplanationService
from emi_copilot.services.ai.audited_weekly_message_writer import AuditedWeeklyMessageWriter
from emi_copilot.services.ai.explanation_flow import ExplanationFlow
from emi_copilot.services.ai.shown_explanation_cache import ShownExplanationCache
from emi_copilot.services.ai.weekly_message_flow import WeeklyMessageFlow
from emi_copilot.services.customer.explanation_types import PlanExplainer
from emi_copilot.services.customer.template_explanation_service import (
    TemplateExplanationService,
)
from emi_copilot.services.weekly_message_writer import WeeklyMessageWriter


def provide_ai_usage_logger(components: ComponentsDependency) -> AiUsageLogger:
    """Gives the usage logger with the configured Sarvam prices (Decimal, from strings)."""
    settings = components.ai.settings
    return AiUsageLogger(
        AiPriceList(
            chat_input_in_rupees_per_million=(
                settings.sarvam_chat_input_price_in_rupees_per_million_tokens
            ),
            chat_output_in_rupees_per_million=(
                settings.sarvam_chat_output_price_in_rupees_per_million_tokens
            ),
            speech_to_text_in_rupees_per_minute=(
                settings.sarvam_speech_to_text_price_in_rupees_per_minute
            ),
            text_to_speech_in_rupees_per_thousand_characters=(
                settings.sarvam_text_to_speech_price_in_rupees_per_thousand_characters
            ),
        )
    )


AiUsageLoggerDependency = Annotated[AiUsageLogger, Depends(provide_ai_usage_logger)]


def provide_shown_explanation_cache(components: ComponentsDependency) -> ShownExplanationCache:
    """Gives the one cache of explanations shown to customer sessions."""
    return components.ai_service_state.shown_explanations


def provide_plan_explainer(
    components: ComponentsDependency, usage_logger: AiUsageLoggerDependency
) -> PlanExplainer:
    """Assembles the audited AI explainer over the template fallback."""
    template = TemplateExplanationService(format_paise_as_whole_rupees)
    flow = ExplanationFlow(components.ai.explanation_text, components.ai.flow_runner, template)
    return AuditedExplanationService(flow, template, usage_logger)


def provide_weekly_message_writer(
    components: ComponentsDependency, usage_logger: AiUsageLoggerDependency
) -> WeeklyMessageWriter:
    """Assembles the audited AI weekly message writer over the Layer 2 template."""
    template = WeeklyMessageTemplate(format_paise_as_whole_rupees)
    flow = WeeklyMessageFlow(components.ai.explanation_text, components.ai.flow_runner, template)
    return AuditedWeeklyMessageWriter(
        flow, template, components.ai_service_state.weekly_messages, usage_logger
    )


ShownExplanationCacheDependency = Annotated[
    ShownExplanationCache, Depends(provide_shown_explanation_cache)
]
PlanExplainerDependency = Annotated[PlanExplainer, Depends(provide_plan_explainer)]
WeeklyMessageWriterDependency = Annotated[
    WeeklyMessageWriter, Depends(provide_weekly_message_writer)
]
