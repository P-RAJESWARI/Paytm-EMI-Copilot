"""TeachBackFlow: deterministic, advisory feedback from the C8 strings and engine figures."""

import pytest

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.teach_back import TeachBackResult
from emi_copilot.services.ai.teach_back_feedback import TeachBackFeedback
from tests.ai_flow_builders import build_teach_back_flow
from tests.sale_builders import build_no_cost_chosen_plan, build_standard_chosen_plan

# The C8 chip shows the monthly figure, a multiplication sign and the tenure.
TIMES = "\u00d7"


def check(
    answer_text: str, language: CustomerLanguage = CustomerLanguage.ENGLISH
) -> TeachBackFeedback:
    """Checks an answer about design plan A (no-cost, ₹3,667 for 6 months, ₹22,000)."""
    return build_teach_back_flow().check(build_no_cost_chosen_plan(), language, answer_text)


@pytest.mark.parametrize(
    "answer_text",
    [
        "I will pay 3667 every month for 6 months",
        "₹3,700 a month, six months",
        "about 3 thousand 7 hundred... no, 3,650 for 6 months",
        # Sarvam speech-to-text writes amounts as words (verified 2026-11-15).
        "three thousand six hundred and sixty seven for six months",
    ],
)
def test_teach_back_flow_close_answer_gets_the_nearly_there_card(answer_text: str) -> None:
    """Digits, number words and rounding within 5% all count; the card restates the terms."""
    feedback = check(answer_text)
    assert feedback.result is TeachBackResult.CLOSE_ENOUGH
    assert feedback.title == "Nearly there"
    assert feedback.body == (
        "You will pay ₹3,667 every month for 6 months. Nothing extra on top of ₹22,000."
    )
    assert feedback.highlighted_terms == (f"₹3,667 {TIMES} 6", "Extra ₹0")
    assert feedback.explain_again_label is None


def test_teach_back_flow_misheard_amount_offers_to_explain_again() -> None:
    """The mockup's again state: what we heard, the correct terms, and "Explain it again"."""
    feedback = check("About ₹3,000 every month")
    assert feedback.result is TeachBackResult.TRY_AGAIN
    assert feedback.heard_text == "About ₹3,000 every month"
    assert feedback.explain_again_label == "Explain it again"


def test_teach_back_flow_answer_without_numbers_tries_again_with_nothing_heard() -> None:
    """No number at all: TRY_AGAIN, and no heard line."""
    feedback = check("I am not sure")
    assert (feedback.result, feedback.heard_text) == (TeachBackResult.TRY_AGAIN, None)


def test_teach_back_flow_in_tamil_uses_the_draft_tamil_strings() -> None:
    """The C8 Tamil strings with the same engine figures."""
    feedback = check("மாதம் ₹3,667, ஆறு மாதங்கள்", CustomerLanguage.TAMIL)
    assert feedback.result is TeachBackResult.CLOSE_ENOUGH
    assert feedback.title == "கிட்டத்தட்ட சரி"
    assert feedback.highlighted_terms == (f"₹3,667 {TIMES} 6", "கூடுதல் ₹0")
    assert "₹22,000-க்கு மேல் கூடுதல் இல்லை" in feedback.body


@pytest.mark.parametrize(
    ("language", "expected_body"),
    [
        (
            CustomerLanguage.ENGLISH,
            "You will pay ₹3,850 every month for 6 months. ₹1,100 extra on top of ₹22,000.",
        ),
        (
            CustomerLanguage.TAMIL,
            "நீங்கள் 6 மாதங்களுக்கு ஒவ்வொரு மாதமும் ₹3,850 செலுத்துவீர்கள். ₹22,000-க்கு மேல் கூடுதலாக ₹1,100.",
        ),
    ],
)
def test_teach_back_flow_plan_with_an_extra_states_the_extra(
    language: CustomerLanguage, expected_body: str
) -> None:
    """Plan B: the extra in total is said on top of the price."""
    feedback = build_teach_back_flow().check(
        build_standard_chosen_plan(), language, "3850, 6 months"
    )
    assert feedback.body == expected_body
    assert feedback.result is TeachBackResult.CLOSE_ENOUGH
