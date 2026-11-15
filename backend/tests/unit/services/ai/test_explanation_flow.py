"""ExplanationFlow: audited AI text, or the template on any failure; AI errors never escape."""

from typing import override

import pytest

from emi_copilot.adapters.ai.flows.flow_runner_port import (
    AiFlowDefinition,
    AiFlowRunnerPort,
    FlowState,
)
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.ai_errors import InvalidAiFlowError
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.number_audit import NumberAuditFailureReason
from emi_copilot.services.ai.ai_flow_types import AiFallbackReason, AiTextSource
from emi_copilot.services.customer.template_explanation_service import TemplateExplanationService
from tests.ai_flow_builders import build_explanation_flow
from tests.fakes.scripted_explanation_text_port import ScriptedExplanationTextPort
from tests.sale_builders import build_no_cost_chosen_plan

PASSING_TEXT = (
    "No-cost EMI from Brand: you pay ₹3,667 each month for 6 months. "
    "The extra you pay in total is ₹0."
)
TEMPLATE_TEXT = (
    TemplateExplanationService(format_paise_as_whole_rupees)
    .explain(build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH)
    .text
)


def explain_text(ai_text: str) -> tuple[str, AiTextSource, tuple[NumberAuditFailureReason, ...]]:
    """Explains design plan A with a scripted AI text; gives the shown text, source and reasons."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: ai_text})
    result = build_explanation_flow(port).explain(
        build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH
    )
    return result.text, result.source, result.audit_failure_reasons


def test_explanation_flow_with_audited_ai_text_shows_it_with_its_usage() -> None:
    """Text that passes the audit is shown as written, with the usage kept for cost."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: PASSING_TEXT})
    result = build_explanation_flow(port).explain(
        build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH
    )
    assert (result.text, result.source, result.fallback_reason) == (
        PASSING_TEXT,
        AiTextSource.AI_AUDITED,
        None,
    )
    assert (result.input_token_count, result.output_token_count) == (120, 30)
    assert len(port.received_requests) == 1


@pytest.mark.parametrize(
    ("ai_text", "expected_reason"),
    [
        (
            PASSING_TEXT.replace("₹3,667", "₹3,676"),
            NumberAuditFailureReason.UNEXPECTED_RUPEE_AMOUNT,
        ),
        (PASSING_TEXT.replace("₹3,667", "₹3,666.67"), NumberAuditFailureReason.UNCHECKABLE_NUMBER),
        (
            PASSING_TEXT.replace(" The extra you pay in total is ₹0.", ""),
            NumberAuditFailureReason.MISSING_REQUIRED_AMOUNT,
        ),
        (f"{PASSING_TEXT} It is the best plan.", NumberAuditFailureReason.FORBIDDEN_WORDING),
        (f"{PASSING_TEXT} About three thousand.", NumberAuditFailureReason.UNCHECKABLE_NUMBER),
        ("", NumberAuditFailureReason.EMPTY_TEXT),
    ],
)
def test_explanation_flow_with_any_audit_failure_shows_the_template(
    ai_text: str, expected_reason: NumberAuditFailureReason
) -> None:
    """A wrong digit, paise, a missing amount, pushy wording or empty text: always the template."""
    text, source, reasons = explain_text(ai_text)
    assert (text, source) == (TEMPLATE_TEXT, AiTextSource.TEMPLATE)
    assert expected_reason in reasons


def test_explanation_flow_with_an_unavailable_provider_shows_the_template_without_raising() -> None:
    """AiTextUnavailableError is caught in the flow and recorded as the fallback reason."""
    port = ScriptedExplanationTextPort({})
    result = build_explanation_flow(port).explain(
        build_no_cost_chosen_plan(), CustomerLanguage.TAMIL
    )
    assert result.source is AiTextSource.TEMPLATE
    assert result.fallback_reason is AiFallbackReason.AI_UNAVAILABLE
    assert (result.input_token_count, result.output_token_count) == (0, 0)


def test_explanation_flow_with_ai_text_switched_off_never_asks_and_shows_the_template() -> None:
    """With no port, the flow goes straight to the template."""
    result = build_explanation_flow(None).explain(
        build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH
    )
    assert (result.text, result.fallback_reason) == (TEMPLATE_TEXT, AiFallbackReason.PROVIDER_OFF)


class RunnerThatRunsNothing(AiFlowRunnerPort):
    """A faulty runner that returns the initial state, to prove the flow notices."""

    @property
    @override
    def runner_name(self) -> str:
        """Gives "faulty"."""
        return "faulty"

    @override
    def run[StateType: FlowState](
        self, flow: AiFlowDefinition[StateType], initial_state: StateType
    ) -> StateType:
        """Skips every step."""
        return initial_state


def test_explanation_flow_with_a_runner_that_skips_the_steps_raises_invalid_flow() -> None:
    """A result must exist; a runner bug is raised, never shown as an empty explanation."""
    flow = build_explanation_flow(None, RunnerThatRunsNothing())
    with pytest.raises(InvalidAiFlowError, match="ended without a result"):
        flow.explain(build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH)
