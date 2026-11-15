"""Both runners give identical results for all three flows, AI passing or falling back."""

from collections.abc import Callable

import pytest

from emi_copilot.adapters.ai.flows.flow_runner_port import AiFlowRunnerPort
from emi_copilot.adapters.ai.flows.langgraph_flow_runner import LangGraphAiFlowRunner
from emi_copilot.adapters.ai.flows.sequential_flow_runner import SequentialAiFlowRunner
from emi_copilot.adapters.ai.mock_explanation_text_adapter import MockExplanationTextAdapter
from emi_copilot.config.ai_settings import MockAiTextBehaviour
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.teach_back import TeachBackResult
from emi_copilot.services.ai.ai_flow_types import AiFallbackReason, AiTextSource
from tests.ai_flow_builders import (
    WEEKLY_ENGLISH_AI_TEXT,
    WEEKLY_TAMIL_AI_TEXT_WITH_A_WRONG_COUNT,
    build_explanation_flow,
    build_teach_back_flow,
    build_weekly_message_flow,
)
from tests.fakes.scripted_explanation_text_port import ScriptedExplanationTextPort
from tests.report_builders import build_design_weekly_message_facts
from tests.sale_builders import build_no_cost_chosen_plan

FlowOutcome = tuple[object, tuple[str, ...]]
"""A flow's full result, and its sources (or teach-back result) for a readable check."""


def explain_with(
    behaviour: MockAiTextBehaviour | None,
) -> Callable[[AiFlowRunnerPort], FlowOutcome]:
    """Explains design plan A with the Mock in a behaviour, or with AI text switched off."""

    def run(runner: AiFlowRunnerPort) -> FlowOutcome:
        """Runs the explanation flow on one runner."""
        port = None if behaviour is None else MockExplanationTextAdapter(behaviour)
        result = build_explanation_flow(port, runner).explain(
            build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH
        )
        fallback = "" if result.fallback_reason is None else result.fallback_reason.value
        return result, (result.source.value, fallback)

    return run


def write_weekly_with(
    port_texts: dict[CustomerLanguage, str] | None,
) -> Callable[[AiFlowRunnerPort], FlowOutcome]:
    """Writes the design week's message with scripted AI texts, or with AI text switched off."""

    def run(runner: AiFlowRunnerPort) -> FlowOutcome:
        """Runs the weekly message flow on one runner."""
        port = None if port_texts is None else ScriptedExplanationTextPort(port_texts)
        result = build_weekly_message_flow(port, runner).write(build_design_weekly_message_facts())
        return result, (result.english.source.value, result.tamil.source.value)

    return run


def teach_back_with(answer_text: str) -> Callable[[AiFlowRunnerPort], FlowOutcome]:
    """Checks a customer's answer about design plan A."""

    def run(runner: AiFlowRunnerPort) -> FlowOutcome:
        """Runs the teach-back flow on one runner."""
        feedback = build_teach_back_flow(runner).check(
            build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH, answer_text
        )
        return feedback, (feedback.result.value,)

    return run


AI_AUDITED, TEMPLATE = AiTextSource.AI_AUDITED.value, AiTextSource.TEMPLATE.value
SCENARIOS: dict[str, tuple[Callable[[AiFlowRunnerPort], FlowOutcome], tuple[str, ...]]] = {
    "explanation-ai-passes-audit": (explain_with(MockAiTextBehaviour.CORRECT), (AI_AUDITED, "")),
    "explanation-wrong-number-gives-template": (
        explain_with(MockAiTextBehaviour.WRONG_NUMBER),
        (TEMPLATE, AiFallbackReason.AUDIT_FAILED.value),
    ),
    "explanation-unavailable-gives-template": (
        explain_with(MockAiTextBehaviour.UNAVAILABLE),
        (TEMPLATE, AiFallbackReason.AI_UNAVAILABLE.value),
    ),
    "explanation-port-off-gives-template": (
        explain_with(None),
        (TEMPLATE, AiFallbackReason.PROVIDER_OFF.value),
    ),
    "weekly-english-kept-tamil-fails-audit": (
        write_weekly_with(
            {
                CustomerLanguage.ENGLISH: WEEKLY_ENGLISH_AI_TEXT,
                CustomerLanguage.TAMIL: WEEKLY_TAMIL_AI_TEXT_WITH_A_WRONG_COUNT,
            }
        ),
        (AI_AUDITED, TEMPLATE),
    ),
    "weekly-unavailable-gives-templates": (write_weekly_with({}), (TEMPLATE, TEMPLATE)),
    "weekly-port-off-gives-templates": (write_weekly_with(None), (TEMPLATE, TEMPLATE)),
    "teach-back-close-enough": (
        teach_back_with("I will pay 3667 every month for 6 months"),
        (TeachBackResult.CLOSE_ENOUGH.value,),
    ),
    "teach-back-try-again": (
        teach_back_with("About ₹3,000 every month"),
        (TeachBackResult.TRY_AGAIN.value,),
    ),
}


@pytest.mark.parametrize("scenario_name", list(SCENARIOS))
def test_flow_runners_sequential_and_langgraph_give_identical_results(scenario_name: str) -> None:
    """The runner is a runtime choice only: both give the same full result in every case."""
    run_scenario, expected_summary = SCENARIOS[scenario_name]
    sequential_result, sequential_summary = run_scenario(SequentialAiFlowRunner())
    langgraph_result, langgraph_summary = run_scenario(LangGraphAiFlowRunner())
    assert sequential_result == langgraph_result
    assert sequential_summary == langgraph_summary == expected_summary
