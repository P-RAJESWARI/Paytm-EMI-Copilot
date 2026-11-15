"""AuditedExplanationService: the C7 explanation written by AI, audited, or else the template."""

import logging
import time
from dataclasses import replace

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import DomainError
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.ai.ai_flow_types import AiFallbackReason, AiTextSource
from emi_copilot.services.ai.ai_usage_logger import (
    AiCallUsage,
    AiUsageLogger,
    measure_elapsed_milliseconds,
)
from emi_copilot.services.ai.explanation_flow import (
    EXPLANATION_FLOW_NAME,
    ExplanationFlow,
    ExplanationFlowResult,
)
from emi_copilot.services.customer.explanation_types import ExplanationSource, ExplanationText
from emi_copilot.services.customer.template_explanation_service import TemplateExplanationService

FLOW_FAILED_OUTCOME = "FLOW_FAILED"
UNKNOWN_MODEL_NAME = "unknown"

audited_explanation_logger = logging.getLogger(__name__)


# Pattern: Decorator. Wraps TemplateExplanationService behind the same PlanExplainer interface and
# adds AI text that must pass the number audit; any failure shows the template text instead.
class AuditedExplanationService:
    """Explains a plan with audited AI text; highlights always come from the engine.

    No AI error ever escapes: provider off, unavailable, audit failure or an unexpected flow
    error all give the template text (CLAUDE.md section 2, rules 1 and 2).
    """

    def __init__(
        self,
        explanation_flow: ExplanationFlow,
        template: TemplateExplanationService,
        usage_logger: AiUsageLogger,
    ) -> None:
        """Keeps the flow, the template fallback and the usage logger."""
        self._explanation_flow = explanation_flow
        self._template = template
        self._usage_logger = usage_logger

    def explain(
        self,
        plan: ChosenPlan,
        language: CustomerLanguage,
        *,
        customer_session_id: str | None = None,
    ) -> ExplanationText:
        """Gives audited AI text, or the template text, with the engine's highlights."""
        template_explanation = self._template.explain(plan, language)
        started_at = time.perf_counter()
        try:
            result = self._explanation_flow.explain(plan, language)
        except DomainError as error:
            audited_explanation_logger.warning(
                "explanation flow failed; template text shown", extra={"error_code": error.code}
            )
            return template_explanation
        self._record_usage(result, measure_elapsed_milliseconds(started_at), customer_session_id)
        if result.source is not AiTextSource.AI_AUDITED:
            return template_explanation
        return replace(template_explanation, text=result.text, source=ExplanationSource.AI_AUDITED)

    def _record_usage(
        self, result: ExplanationFlowResult, latency_ms: int, customer_session_id: str | None
    ) -> None:
        """Logs the AI call's usage; nothing is logged when AI text is switched off (no call)."""
        if result.fallback_reason is AiFallbackReason.PROVIDER_OFF:
            return
        self._usage_logger.record_chat_call(
            AiCallUsage(
                flow=EXPLANATION_FLOW_NAME,
                model=result.model_name or UNKNOWN_MODEL_NAME,
                latency_ms=latency_ms,
                model_input_usage_count=result.input_token_count,
                model_output_usage_count=result.output_token_count,
                outcome=(result.fallback_reason or result.source).value,
                customer_session_id=customer_session_id,
            )
        )
