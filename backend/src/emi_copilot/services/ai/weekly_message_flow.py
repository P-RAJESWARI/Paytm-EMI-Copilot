"""WeeklyMessageFlow: write English and Tamil -> audit each -> choose per language.

Each language is decided on its own: a Tamil text that fails the audit falls back to the Tamil
template while an audited English text is kept, and the other way round.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.flows.flow_runner_port import (
    AiFlowDefinition,
    AiFlowRunnerPort,
    AiFlowStep,
)
from emi_copilot.domain.ai_errors import AiProviderError
from emi_copilot.domain.number_audit import (
    AllowedNumbers,
    NumberAuditFailureReason,
    NumberAuditService,
)
from emi_copilot.domain.reports.weekly_message_template import (
    WeeklyMessageFacts,
    WeeklyMessageTemplate,
    WeeklyMessageText,
)
from emi_copilot.domain.reports.weekly_message_wording import MessageLanguage
from emi_copilot.services.ai.ai_flow_types import (
    AiFallbackReason,
    AiTextSource,
    require_flow_result,
)
from emi_copilot.services.ai.weekly_message_prompt_builder import WeeklyMessagePromptBuilder

WEEKLY_MESSAGE_FLOW_NAME = "weekly_message"


@dataclass(frozen=True, slots=True)
class WeeklyLanguageDraft:
    """One language's AI text so far, or why it will not be used."""

    ai_text: str = ""
    fallback_reason: AiFallbackReason | None = None
    audit_failure_reasons: tuple[NumberAuditFailureReason, ...] = ()
    input_token_count: int = 0
    output_token_count: int = 0
    model_name: str | None = None


@dataclass(frozen=True, slots=True)
class WeeklyLanguageResult:
    """One language's message as shown, with who wrote it, why not AI, and the usage."""

    message: WeeklyMessageText
    source: AiTextSource
    fallback_reason: AiFallbackReason | None
    audit_failure_reasons: tuple[NumberAuditFailureReason, ...]
    input_token_count: int
    output_token_count: int
    model_name: str | None


@dataclass(frozen=True, slots=True)
class WeeklyMessageFlowResult:
    """The week's message in English and in Tamil, each with its own source."""

    english: WeeklyLanguageResult
    tamil: WeeklyLanguageResult


@dataclass(frozen=True, slots=True)
class WeeklyMessageFlowState:
    """What the weekly message flow knows so far; each step returns a new state."""

    facts: WeeklyMessageFacts
    drafts: Mapping[MessageLanguage, WeeklyLanguageDraft] = MappingProxyType({})
    result: WeeklyMessageFlowResult | None = None

    @property
    def has_finished(self) -> bool:
        """Tells whether both languages' texts are decided."""
        return self.result is not None


def _per_language(
    drafts: dict[MessageLanguage, WeeklyLanguageDraft],
) -> Mapping[MessageLanguage, WeeklyLanguageDraft]:
    """Freezes one draft per language, so a later step cannot change an earlier state."""
    return MappingProxyType(dict(drafts))


class WeeklyMessageFlow:
    """Writes the shop's weekly message with audited AI text, per language, or the template."""

    def __init__(
        self,
        explanation_text: ExplanationTextPort | None,
        flow_runner: AiFlowRunnerPort,
        template: WeeklyMessageTemplate,
    ) -> None:
        """Keeps the AI port (None when switched off), the runner and the template fallback."""
        self._explanation_text = explanation_text
        self._flow_runner = flow_runner
        self._template = template
        self._prompt_builder = WeeklyMessagePromptBuilder()
        self._audit_service = NumberAuditService()
        self._definition = AiFlowDefinition(
            WEEKLY_MESSAGE_FLOW_NAME,
            (
                AiFlowStep("write_each_language", self._write),
                AiFlowStep("audit_each_language", self._audit),
                AiFlowStep("choose_per_language", self._choose),
            ),
        )

    def write(self, facts: WeeklyMessageFacts) -> WeeklyMessageFlowResult:
        """Runs the flow; AI errors never escape it, they become template text."""
        final_state = self._flow_runner.run(self._definition, WeeklyMessageFlowState(facts))
        return require_flow_result(final_state.result, WEEKLY_MESSAGE_FLOW_NAME)

    def _write(self, state: WeeklyMessageFlowState) -> WeeklyMessageFlowState:
        """Asks for both languages; with AI switched off, both use the template at once."""
        if self._explanation_text is None:
            off = WeeklyLanguageDraft(fallback_reason=AiFallbackReason.PROVIDER_OFF)
            return self._choose(
                replace(state, drafts=_per_language(dict.fromkeys(MessageLanguage, off)))
            )
        return replace(
            state,
            drafts=_per_language(
                {
                    language: self._write_one(self._explanation_text, state.facts, language)
                    for language in MessageLanguage
                }
            ),
        )

    def _write_one(
        self, port: ExplanationTextPort, facts: WeeklyMessageFacts, language: MessageLanguage
    ) -> WeeklyLanguageDraft:
        """Writes one language; an unavailable provider marks only that language for fallback."""
        try:
            completion = port.write_text(self._prompt_builder.build(facts, language))
        except AiProviderError:
            return WeeklyLanguageDraft(fallback_reason=AiFallbackReason.AI_UNAVAILABLE)
        return WeeklyLanguageDraft(
            ai_text=completion.text,
            input_token_count=completion.input_token_count,
            output_token_count=completion.output_token_count,
            model_name=completion.model_name,
        )

    def _audit(self, state: WeeklyMessageFlowState) -> WeeklyMessageFlowState:
        """Audits each written language against the week's allowed figures."""
        allowed = AllowedNumbers.for_weekly_message(state.facts)
        return replace(
            state,
            drafts=_per_language(
                {
                    language: self._audit_one(draft, allowed)
                    for language, draft in state.drafts.items()
                }
            ),
        )

    def _audit_one(
        self, draft: WeeklyLanguageDraft, allowed: AllowedNumbers
    ) -> WeeklyLanguageDraft:
        """Marks one written language for fallback when its text fails the audit."""
        if draft.fallback_reason is not None:
            return draft
        failure_reasons = self._audit_service.audit(draft.ai_text, allowed, ()).failure_reasons
        if not failure_reasons:
            return draft
        return replace(
            draft,
            fallback_reason=AiFallbackReason.AUDIT_FAILED,
            audit_failure_reasons=failure_reasons,
        )

    def _choose(self, state: WeeklyMessageFlowState) -> WeeklyMessageFlowState:
        """Keeps each audited AI text under the template's title; the template otherwise."""
        return replace(
            state,
            result=WeeklyMessageFlowResult(
                english=self._choose_one(state, MessageLanguage.ENGLISH),
                tamil=self._choose_one(state, MessageLanguage.TAMIL),
            ),
        )

    def _choose_one(
        self, state: WeeklyMessageFlowState, language: MessageLanguage
    ) -> WeeklyLanguageResult:
        """Gives one language's message: the audited AI text, or the template message."""
        draft = state.drafts[language]
        template_message = self._template.render_in(language, state.facts)
        is_ai_text_used = draft.fallback_reason is None
        return WeeklyLanguageResult(
            message=(
                WeeklyMessageText(title=template_message.title, paragraphs=(draft.ai_text,))
                if is_ai_text_used
                else template_message
            ),
            source=AiTextSource.AI_AUDITED if is_ai_text_used else AiTextSource.TEMPLATE,
            fallback_reason=draft.fallback_reason,
            audit_failure_reasons=draft.audit_failure_reasons,
            input_token_count=draft.input_token_count,
            output_token_count=draft.output_token_count,
            model_name=draft.model_name,
        )
