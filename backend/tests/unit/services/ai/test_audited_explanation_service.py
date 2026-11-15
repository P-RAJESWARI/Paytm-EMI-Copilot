"""AuditedExplanationService: audited AI text or the template, engine highlights, safe logs."""

import logging
from typing import override

import pytest

from emi_copilot.adapters.ai.flows.flow_runner_port import (
    AiFlowDefinition,
    AiFlowRunnerPort,
    FlowState,
)
from emi_copilot.adapters.ai.mock_explanation_text_adapter import MockExplanationTextAdapter
from emi_copilot.config.ai_settings import MockAiTextBehaviour
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.ai_errors import InvalidAiFlowError
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.services.ai.ai_usage_logger import AI_CALL_LOG_MESSAGE, AiUsageLogger
from emi_copilot.services.ai.audited_explanation_service import AuditedExplanationService
from emi_copilot.services.ai.explanation_flow import ExplanationFlow
from emi_copilot.services.customer.explanation_types import (
    ExplanationSource,
    ExplanationText,
    highlight_plan_figures,
)
from emi_copilot.services.customer.template_explanation_service import TemplateExplanationService
from tests.ai_flow_builders import TEST_AI_PRICE_LIST, build_explanation_flow
from tests.fakes.scripted_explanation_text_port import ScriptedExplanationTextPort
from tests.sale_builders import build_no_cost_chosen_plan

TEMPLATE = TemplateExplanationService(format_paise_as_whole_rupees)
PASSING_TEXT = (
    "No-cost EMI from Brand: you pay ₹3,667 each month for 6 months. "
    "The extra you pay in total is ₹0."
)
SESSION_ID = "01JCSESSION0000000000000001"


def build_service(explanation_flow: ExplanationFlow) -> AuditedExplanationService:
    """Wraps the flow with the real template and a logger on the default prices."""
    return AuditedExplanationService(explanation_flow, TEMPLATE, AiUsageLogger(TEST_AI_PRICE_LIST))


def explain_with(flow: ExplanationFlow) -> ExplanationText:
    """Explains design plan A in English for the test session."""
    return build_service(flow).explain(
        build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH, customer_session_id=SESSION_ID
    )


def template_text() -> ExplanationText:
    """The template explanation of design plan A in English."""
    return TEMPLATE.explain(build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH)


def test_audited_explanation_service_ai_text_with_wrong_digit_returns_template_text() -> None:
    """The Mock changes one digit of ₹3,667; the audit fails, so the template text is shown."""
    explanation = explain_with(
        build_explanation_flow(MockExplanationTextAdapter(MockAiTextBehaviour.WRONG_NUMBER))
    )
    assert explanation == template_text()


def test_audited_explanation_service_ai_unavailable_returns_template_text() -> None:
    """An unavailable provider is no error to the customer: the template text is shown."""
    explanation = explain_with(
        build_explanation_flow(MockExplanationTextAdapter(MockAiTextBehaviour.UNAVAILABLE))
    )
    assert explanation == template_text()


def test_audited_explanation_service_text_off_returns_template_text_without_usage_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With AI text switched off no call is made, so no usage line is written."""
    with caplog.at_level(logging.INFO):
        explanation = explain_with(build_explanation_flow(None))
    assert explanation == template_text()
    assert not [record for record in caplog.records if record.message == AI_CALL_LOG_MESSAGE]


def test_audited_explanation_service_passing_text_is_ai_audited_with_engine_highlights() -> None:
    """Audited AI text is shown as AI_AUDITED; the highlights are the engine's, not the AI's."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: PASSING_TEXT})
    explanation = explain_with(build_explanation_flow(port))
    assert explanation.text == PASSING_TEXT
    assert explanation.source is ExplanationSource.AI_AUDITED
    assert explanation.highlighted_amounts == highlight_plan_figures(build_no_cost_chosen_plan())


class FailingFlowRunner(AiFlowRunnerPort):
    """A runner that fails as a broken flow definition would."""

    @property
    @override
    def runner_name(self) -> str:
        """Gives "failing"."""
        return "failing"

    @override
    def run[StateType: FlowState](
        self, flow: AiFlowDefinition[StateType], initial_state: StateType
    ) -> StateType:
        """Raises the typed flow error."""
        raise InvalidAiFlowError("Broken on purpose.")


def test_audited_explanation_service_flow_error_never_escapes() -> None:
    """Even an unexpected typed flow error gives the template text."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: PASSING_TEXT})
    explanation = explain_with(build_explanation_flow(port, FailingFlowRunner()))
    assert explanation == template_text()


def test_audited_explanation_service_usage_log_line_carries_counts_and_cost_but_no_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One line with flow, model, usage, cost and session id; no prompt or completion text."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: PASSING_TEXT})
    with caplog.at_level(logging.INFO):
        explain_with(build_explanation_flow(port))
    (usage_record,) = [record for record in caplog.records if record.message == AI_CALL_LOG_MESSAGE]
    fields = vars(usage_record)
    assert fields["ai_flow"] == "plan_explanation"
    assert fields["ai_model"] == "scripted-text"
    assert fields["ai_outcome"] == "AI_AUDITED"
    assert fields["customer_session_id"] == SESSION_ID
    assert (fields["model_input_usage_count"], fields["model_output_usage_count"]) == (120, 30)
    # 120 x ₹15 + 30 x ₹60 per million tokens = ₹0.0036.
    assert fields["estimated_cost_in_rupees"] == "0.003600"
    assert isinstance(fields["latency_ms"], int)
    every_value = " ".join(str(value) for value in fields.values())
    assert "₹3,667" not in every_value
    assert "No-cost EMI" not in every_value
