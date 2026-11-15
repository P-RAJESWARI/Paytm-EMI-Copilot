"""WeeklyMessageFlow: each language is audited and falls back on its own."""

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.number_audit import NumberAuditFailureReason
from emi_copilot.domain.reports.weekly_message_wording import MessageLanguage
from emi_copilot.services.ai.ai_flow_types import AiFallbackReason, AiTextSource
from tests.ai_flow_builders import (
    WEEKLY_ENGLISH_AI_TEXT,
    WEEKLY_TAMIL_AI_TEXT,
    WEEKLY_TAMIL_AI_TEXT_WITH_A_WRONG_COUNT,
    build_weekly_message_flow,
    render_weekly_template,
)
from tests.fakes.scripted_explanation_text_port import ScriptedExplanationTextPort
from tests.report_builders import build_design_weekly_message_facts


def test_weekly_message_flow_tamil_fails_audit_english_kept() -> None:
    """A wrong Tamil count falls back to the Tamil template; the audited English is kept."""
    port = ScriptedExplanationTextPort(
        {
            CustomerLanguage.ENGLISH: WEEKLY_ENGLISH_AI_TEXT,
            CustomerLanguage.TAMIL: WEEKLY_TAMIL_AI_TEXT_WITH_A_WRONG_COUNT,
        }
    )
    facts = build_design_weekly_message_facts()
    result = build_weekly_message_flow(port).write(facts)
    english_template = render_weekly_template(MessageLanguage.ENGLISH, facts)
    assert result.english.source is AiTextSource.AI_AUDITED
    assert result.english.message.title == english_template.title
    assert result.english.message.paragraphs == (WEEKLY_ENGLISH_AI_TEXT,)
    assert (result.english.input_token_count, result.english.output_token_count) == (120, 30)
    assert result.tamil.source is AiTextSource.TEMPLATE
    assert result.tamil.fallback_reason is AiFallbackReason.AUDIT_FAILED
    assert result.tamil.audit_failure_reasons == (NumberAuditFailureReason.UNEXPECTED_PLAIN_NUMBER,)
    assert result.tamil.message == render_weekly_template(MessageLanguage.TAMIL, facts)


def test_weekly_message_flow_with_both_texts_audited_keeps_both() -> None:
    """Both languages pass, so both show the AI text under the template's title."""
    port = ScriptedExplanationTextPort(
        {
            CustomerLanguage.ENGLISH: WEEKLY_ENGLISH_AI_TEXT,
            CustomerLanguage.TAMIL: WEEKLY_TAMIL_AI_TEXT,
        }
    )
    result = build_weekly_message_flow(port).write(build_design_weekly_message_facts())
    assert (result.english.source, result.tamil.source) == (AiTextSource.AI_AUDITED,) * 2
    assert result.tamil.message.paragraphs == (WEEKLY_TAMIL_AI_TEXT,)
    assert len(port.received_requests) == 2


def test_weekly_message_flow_with_one_language_unavailable_falls_back_for_that_one() -> None:
    """An unavailable Tamil call does not stop the English text."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: WEEKLY_ENGLISH_AI_TEXT})
    result = build_weekly_message_flow(port).write(build_design_weekly_message_facts())
    assert result.english.source is AiTextSource.AI_AUDITED
    assert result.tamil.fallback_reason is AiFallbackReason.AI_UNAVAILABLE


def test_weekly_message_flow_with_ai_text_switched_off_gives_both_templates() -> None:
    """With no port, both languages are the template at once."""
    facts = build_design_weekly_message_facts()
    result = build_weekly_message_flow(None).write(facts)
    assert result.english.fallback_reason is AiFallbackReason.PROVIDER_OFF
    assert result.english.message == render_weekly_template(MessageLanguage.ENGLISH, facts)
    assert result.tamil.message == render_weekly_template(MessageLanguage.TAMIL, facts)
