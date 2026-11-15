"""ExplanationTextPort contract: the labelled Mock and the Sarvam adapter (on fixtures) agree.

Both write design plan A's explanation that passes the number audit, and both report failure
with AiTextUnavailableError. The Sarvam side answers from documented-shape fixtures [Verify].
"""

from collections.abc import Callable

import pytest

from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.mock_explanation_text_adapter import MockExplanationTextAdapter
from emi_copilot.config.ai_settings import MockAiTextBehaviour
from emi_copilot.domain.ai_errors import AiTextUnavailableError
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.number_audit import AllowedNumbers, NumberAuditService
from emi_copilot.services.ai.explanation_prompt_builder import ExplanationPromptBuilder
from tests.sale_builders import build_no_cost_chosen_plan
from tests.sarvam_builders import (
    build_sarvam_chat_text_adapter,
    build_scripted_client,
    fixture_response,
)

PLAN_A_REQUIRED_AMOUNTS = (3667, 0)


def build_sarvam_port(fixture_name: str, status_code: int) -> ExplanationTextPort:
    """Builds the Sarvam chat adapter answering one fixture."""
    return build_sarvam_chat_text_adapter(
        build_scripted_client([fixture_response(status_code, fixture_name)], "sarvam-chat")
    )


WORKING_PORT_BUILDERS: dict[str, Callable[[], ExplanationTextPort]] = {
    "mock": MockExplanationTextAdapter,
    "sarvam": lambda: build_sarvam_port("chat_success.json", 200),
}
FAILING_PORT_BUILDERS: dict[str, Callable[[], ExplanationTextPort]] = {
    "mock-unavailable": lambda: MockExplanationTextAdapter(MockAiTextBehaviour.UNAVAILABLE),
    "sarvam-length": lambda: build_sarvam_port("chat_length.json", 200),
    "sarvam-429": lambda: build_sarvam_port("chat_error_429.json", 429),
}


@pytest.mark.parametrize("port_name", sorted(WORKING_PORT_BUILDERS))
def test_explanation_text_port_writes_text_that_passes_the_number_audit(port_name: str) -> None:
    """Design plan A in English: the monthly ₹3,667 and the ₹0 extra, nothing else."""
    plan = build_no_cost_chosen_plan()
    request = ExplanationPromptBuilder().build(plan, CustomerLanguage.ENGLISH)
    completion = WORKING_PORT_BUILDERS[port_name]().write_text(request)
    allowed = AllowedNumbers.for_plan_explanation(plan, label_texts=(plan.lender_label,))
    result = NumberAuditService().audit(completion.text, allowed, PLAN_A_REQUIRED_AMOUNTS)
    assert result.has_passed, (completion.text, result)
    assert completion.finish_reason == "stop"
    assert completion.output_token_count > 0


@pytest.mark.parametrize("port_name", sorted(FAILING_PORT_BUILDERS))
def test_explanation_text_port_failure_raises_ai_text_unavailable(port_name: str) -> None:
    """Every failure is the one typed error the audited explainer falls back on."""
    request = ExplanationPromptBuilder().build(
        build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH
    )
    with pytest.raises(AiTextUnavailableError):
        FAILING_PORT_BUILDERS[port_name]().write_text(request)
