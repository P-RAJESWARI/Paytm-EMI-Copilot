"""ExplanationFlow: write -> audit -> choose, so the customer sees audited AI text or the template.

AI never touches the money path: the figures come from the engine, the AI text is checked by the
number audit, and any failure (provider off, unavailable, or audit) shows the template text.
"""

from dataclasses import dataclass, replace

from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.flows.flow_runner_port import (
    AiFlowDefinition,
    AiFlowRunnerPort,
    AiFlowStep,
)
from emi_copilot.domain.ai_errors import AiProviderError
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.number_audit import (
    AllowedNumbers,
    NumberAuditFailureReason,
    NumberAuditService,
)
from emi_copilot.domain.number_audit.allowed_numbers import whole_rupees_of
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.ai.ai_flow_types import (
    AiFallbackReason,
    AiTextSource,
    require_flow_result,
)
from emi_copilot.services.ai.explanation_prompt_builder import (
    ExplanationPromptBuilder,
    build_explanation_prompt_facts,
)
from emi_copilot.services.customer.template_explanation_service import TemplateExplanationService

EXPLANATION_FLOW_NAME = "plan_explanation"


@dataclass(frozen=True, slots=True)
class ExplanationFlowResult:
    """The C7 text and its evidence: who wrote it, why not AI, and the usage for cost."""

    text: str
    source: AiTextSource
    fallback_reason: AiFallbackReason | None
    audit_failure_reasons: tuple[NumberAuditFailureReason, ...]
    input_token_count: int
    output_token_count: int


@dataclass(frozen=True, slots=True)
class ExplanationFlowState:
    """What the explanation flow knows so far; each step returns a new state."""

    plan: ChosenPlan
    language: CustomerLanguage
    ai_text: str = ""
    input_token_count: int = 0
    output_token_count: int = 0
    audit_failure_reasons: tuple[NumberAuditFailureReason, ...] = ()
    result: ExplanationFlowResult | None = None

    @property
    def has_finished(self) -> bool:
        """Tells whether the text to show is decided."""
        return self.result is not None


class ExplanationFlow:
    """Explains one chosen plan with audited AI text, falling back to the template text."""

    def __init__(
        self,
        explanation_text: ExplanationTextPort | None,
        flow_runner: AiFlowRunnerPort,
        template: TemplateExplanationService,
    ) -> None:
        """Keeps the AI port (None when switched off), the runner and the template fallback."""
        self._explanation_text = explanation_text
        self._flow_runner = flow_runner
        self._template = template
        self._prompt_builder = ExplanationPromptBuilder()
        self._audit_service = NumberAuditService()
        self._definition = AiFlowDefinition(
            EXPLANATION_FLOW_NAME,
            (
                AiFlowStep("write", self._write),
                AiFlowStep("audit", self._audit),
                AiFlowStep("choose", self._choose),
            ),
        )

    def explain(self, plan: ChosenPlan, language: CustomerLanguage) -> ExplanationFlowResult:
        """Runs the flow; AI errors never escape it, they become a template result."""
        final_state = self._flow_runner.run(self._definition, ExplanationFlowState(plan, language))
        return require_flow_result(final_state.result, EXPLANATION_FLOW_NAME)

    def _write(self, state: ExplanationFlowState) -> ExplanationFlowState:
        """Asks the AI port for text; provider off or unavailable finishes with the template."""
        if self._explanation_text is None:
            return self._finish_with_template(state, AiFallbackReason.PROVIDER_OFF)
        request = self._prompt_builder.build(state.plan, state.language)
        try:
            completion = self._explanation_text.write_text(request)
        except AiProviderError:
            return self._finish_with_template(state, AiFallbackReason.AI_UNAVAILABLE)
        return replace(
            state,
            ai_text=completion.text,
            input_token_count=completion.input_token_count,
            output_token_count=completion.output_token_count,
        )

    def _audit(self, state: ExplanationFlowState) -> ExplanationFlowState:
        """Checks every number and phrase; the monthly and the extra must both be mentioned."""
        plan = state.plan
        facts = build_explanation_prompt_facts(plan, state.language)
        result = self._audit_service.audit(
            state.ai_text,
            AllowedNumbers.for_plan_explanation(
                plan, label_texts=(plan.lender_label, facts.plan_display_name)
            ),
            required_rupee_amounts=(
                whole_rupees_of(plan.monthly_installment),
                whole_rupees_of(plan.extra_in_total),
            ),
        )
        return replace(state, audit_failure_reasons=result.failure_reasons)

    def _choose(self, state: ExplanationFlowState) -> ExplanationFlowState:
        """Shows the AI text only when it passed the audit; otherwise the template text."""
        if state.audit_failure_reasons:
            return self._finish_with_template(state, AiFallbackReason.AUDIT_FAILED)
        return replace(
            state,
            result=ExplanationFlowResult(
                text=state.ai_text,
                source=AiTextSource.AI_AUDITED,
                fallback_reason=None,
                audit_failure_reasons=(),
                input_token_count=state.input_token_count,
                output_token_count=state.output_token_count,
            ),
        )

    def _finish_with_template(
        self, state: ExplanationFlowState, fallback_reason: AiFallbackReason
    ) -> ExplanationFlowState:
        """Finishes the flow with the template text, keeping the reason and any usage spent."""
        return replace(
            state,
            result=ExplanationFlowResult(
                text=self._template.explain(state.plan, state.language).text,
                source=AiTextSource.TEMPLATE,
                fallback_reason=fallback_reason,
                audit_failure_reasons=state.audit_failure_reasons,
                input_token_count=state.input_token_count,
                output_token_count=state.output_token_count,
            ),
        )
