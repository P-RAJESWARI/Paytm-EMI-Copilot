"""MockExplanationTextAdapter copies facts exactly, or fails on purpose when configured to."""

import json
import logging

import pytest

from emi_copilot.adapters.ai.ai_types import AiTextRequest
from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.mock_explanation_text_adapter import (
    MOCK_TEXT_MODEL_NAME,
    MockExplanationTextAdapter,
    change_one_digit,
    humanise_fact_name,
)
from emi_copilot.config.ai_settings import MockAiTextBehaviour
from emi_copilot.domain.ai_errors import AiTextUnavailableError
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.number_audit import AllowedNumbers, NumberAuditService
from emi_copilot.domain.number_audit.allowed_numbers import whole_rupees_of
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.ai.explanation_prompt_builder import ExplanationPromptBuilder
from tests.sale_builders import build_no_cost_chosen_plan, build_standard_chosen_plan

DESIGN_PLAN_A_FACTS = {
    "planName": "No-cost EMI",
    "monthlyAmount": "₹3,667",
    "tenureInMonths": 6,
    "extra_in_total": "₹0",
    "fundedBy": None,
}


def build_request(language: CustomerLanguage = CustomerLanguage.ENGLISH) -> AiTextRequest:
    """Builds a request for the design's plan A, the no-cost plan on ₹22,000."""
    return AiTextRequest(
        system_instruction="Explain the plan in plain words.",
        structured_facts_json=json.dumps(DESIGN_PLAN_A_FACTS, ensure_ascii=False),
        language=language,
    )


def list_digits(text: str) -> list[str]:
    """Lists the ASCII digits of a text in order."""
    return [character for character in text if character.isascii() and character.isdigit()]


def test_mock_text_adapter_built_announces_itself_with_its_behaviour(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Rule 10: the Mock is named in the startup log together with how it behaves."""
    with caplog.at_level(logging.WARNING):
        adapter = MockExplanationTextAdapter(MockAiTextBehaviour.WRONG_NUMBER)
    assert isinstance(adapter, ExplanationTextPort)
    (record,) = caplog.records
    assert "MockExplanationTextAdapter active" in record.getMessage()
    assert "wrong_number" in record.getMessage()


def test_mock_text_adapter_correct_copies_every_fact_exactly() -> None:
    """Only numbers from the facts appear, so the text later passes the number audit."""
    completion = MockExplanationTextAdapter().write_text(build_request())
    assert completion.text == (
        "Here are the plan facts in plain words. plan name: No-cost EMI. "
        "monthly amount: ₹3,667. tenure in months: 6. extra in total: ₹0. funded by: null."
    )
    assert completion.model_name == MOCK_TEXT_MODEL_NAME
    assert completion.finish_reason == "stop"
    assert completion.input_token_count > 0
    assert completion.output_token_count == len(completion.text.split())


def test_mock_text_adapter_tamil_request_opens_with_a_tamil_sentence() -> None:
    """The opening sentence follows the customer's language; the facts are copied as given."""
    completion = MockExplanationTextAdapter().write_text(build_request(CustomerLanguage.TAMIL))
    assert completion.text.startswith("திட்டத்தின் விவரங்கள்")
    assert "₹3,667" in completion.text


def test_mock_text_adapter_is_deterministic() -> None:
    """The same request always gives the same text, so tests and caches are stable."""
    adapter = MockExplanationTextAdapter()
    assert adapter.write_text(build_request()) == adapter.write_text(build_request())


def test_mock_text_adapter_wrong_number_changes_exactly_one_digit_of_the_first_amount() -> None:
    """The first rupee amount ₹3,667 becomes ₹4,667; every other digit is untouched."""
    correct_text = MockExplanationTextAdapter().write_text(build_request()).text
    wrong_text = (
        MockExplanationTextAdapter(MockAiTextBehaviour.WRONG_NUMBER)
        .write_text(build_request())
        .text
    )
    assert "₹4,667" in wrong_text
    correct_digits, wrong_digits = list_digits(correct_text), list_digits(wrong_text)
    assert len(correct_digits) == len(wrong_digits)
    assert (
        sum(1 for pair in zip(correct_digits, wrong_digits, strict=True) if len(set(pair)) > 1) == 1
    )


def test_mock_text_adapter_unavailable_raises_ai_text_unavailable() -> None:
    """The template fallback path can be shown without a network failure."""
    adapter = MockExplanationTextAdapter(MockAiTextBehaviour.UNAVAILABLE)
    with pytest.raises(AiTextUnavailableError, match="MOCK_AI_TEXT_BEHAVIOUR"):
        adapter.write_text(build_request())


@pytest.mark.parametrize(
    ("text", "expected_text"),
    [
        ("pay ₹9,000 for 6 months", "pay ₹0,000 for 6 months"),
        ("pay ₹ 3,667", "pay ₹ 4,667"),
        ("6 months, no amount", "7 months, no amount"),
        ("no digits at all", "no digits at all"),
    ],
)
def test_change_one_digit_prefers_the_first_rupee_amount(text: str, expected_text: str) -> None:
    """A rupee amount is changed first, else the first digit; text without digits is kept."""
    assert change_one_digit(text) == expected_text


@pytest.mark.parametrize(
    ("fact_name", "expected_words"),
    [("monthlyAmount", "monthly amount"), ("extra_in_total", "extra in total"), ("x", "x")],
)
def test_humanise_fact_name_splits_camel_and_snake_case(
    fact_name: str, expected_words: str
) -> None:
    """Fact names read as lower-case words in the Mock's text."""
    assert humanise_fact_name(fact_name) == expected_words


@pytest.mark.parametrize("language", list(CustomerLanguage))
@pytest.mark.parametrize("plan", [build_no_cost_chosen_plan(), build_standard_chosen_plan()])
def test_mock_text_adapter_correct_explanation_passes_the_number_audit(
    plan: ChosenPlan, language: CustomerLanguage
) -> None:
    """Given typed plan facts, the Mock writes two sentences the audit accepts."""
    request = ExplanationPromptBuilder().build(plan, language)
    text = MockExplanationTextAdapter().write_text(request).text
    allowed = AllowedNumbers.for_plan_explanation(plan, label_texts=(plan.lender_label,))
    required = (whole_rupees_of(plan.monthly_installment), whole_rupees_of(plan.extra_in_total))
    assert NumberAuditService().audit(text, allowed, required).has_passed, text


def test_mock_text_adapter_explains_design_plan_a_in_plain_english() -> None:
    """The monthly figure, the tenure and the extra, formatted as the screens show them."""
    request = ExplanationPromptBuilder().build(
        build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH
    )
    assert MockExplanationTextAdapter().write_text(request).text == (
        "No-cost EMI from Brand: ₹3,667 each month for 6 months. The extra you pay in total is ₹0."
    )


def test_mock_text_adapter_wrong_number_explanation_fails_the_number_audit() -> None:
    """MOCK_AI_TEXT_BEHAVIOUR=wrong_number shows the template fallback in the demo."""
    plan = build_no_cost_chosen_plan()
    request = ExplanationPromptBuilder().build(plan, CustomerLanguage.ENGLISH)
    text = MockExplanationTextAdapter(MockAiTextBehaviour.WRONG_NUMBER).write_text(request).text
    allowed = AllowedNumbers.for_plan_explanation(plan, label_texts=(plan.lender_label,))
    result = NumberAuditService().audit(text, allowed, (3667, 0))
    assert result.has_passed is False
    assert result.mismatched_tokens == ("₹4,667",)
