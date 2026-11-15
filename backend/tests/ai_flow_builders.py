"""Builders of the three AI flows for tests, on the design sample data and in-memory ports."""

from decimal import Decimal

from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.flows.flow_runner_port import AiFlowRunnerPort
from emi_copilot.adapters.ai.flows.sequential_flow_runner import SequentialAiFlowRunner
from emi_copilot.core.clock import Clock
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.reports.weekly_message_template import (
    WeeklyMessageFacts,
    WeeklyMessageTemplate,
    WeeklyMessageText,
)
from emi_copilot.domain.reports.weekly_message_wording import MessageLanguage
from emi_copilot.services.ai.ai_usage_logger import AiPriceList, AiUsageLogger
from emi_copilot.services.ai.audited_weekly_message_writer import (
    AuditedWeeklyMessageWriter,
    build_weekly_message_cache,
)
from emi_copilot.services.ai.explanation_flow import ExplanationFlow
from emi_copilot.services.ai.teach_back_feedback import TeachBackFeedbackWriter
from emi_copilot.services.ai.teach_back_flow import TeachBackFlow
from emi_copilot.services.ai.weekly_message_flow import WeeklyMessageFlow
from emi_copilot.services.customer.template_explanation_service import TemplateExplanationService

# The design week's figures (DESIGN_SPEC section 4), as an AI might write them.
WEEKLY_ENGLISH_AI_TEXT = (
    "44 of 120 customers bought on EMI this week. ₹1,84,000 is due from brands, with a payment "
    "around 13 January 2027."
)
# draft: needs native review
WEEKLY_TAMIL_AI_TEXT = "120 வாடிக்கையாளர்களில் 44 பேர் EMI-யில் வாங்கினர்."
# One wrong digit: 45 customers instead of 44.
WEEKLY_TAMIL_AI_TEXT_WITH_A_WRONG_COUNT = "120 வாடிக்கையாளர்களில் 45 பேர் EMI-யில் வாங்கினர்."

# The AiSettings default prices, so cost estimates in tests match a default configuration.
TEST_AI_PRICE_LIST = AiPriceList(
    chat_input_in_rupees_per_million=Decimal("15"),
    chat_output_in_rupees_per_million=Decimal("60"),
    speech_to_text_in_rupees_per_minute=Decimal("0.49"),
    text_to_speech_in_rupees_per_thousand_characters=Decimal("3.00"),
)


def build_explanation_flow(
    explanation_text: ExplanationTextPort | None, flow_runner: AiFlowRunnerPort | None = None
) -> ExplanationFlow:
    """Builds the explanation flow with the real template fallback."""
    return ExplanationFlow(
        explanation_text,
        flow_runner or SequentialAiFlowRunner(),
        TemplateExplanationService(format_paise_as_whole_rupees),
    )


def build_weekly_message_flow(
    explanation_text: ExplanationTextPort | None, flow_runner: AiFlowRunnerPort | None = None
) -> WeeklyMessageFlow:
    """Builds the weekly message flow with the real template fallback."""
    return WeeklyMessageFlow(
        explanation_text,
        flow_runner or SequentialAiFlowRunner(),
        WeeklyMessageTemplate(format_paise_as_whole_rupees),
    )


def build_teach_back_flow(flow_runner: AiFlowRunnerPort | None = None) -> TeachBackFlow:
    """Builds the teach-back flow with the real feedback wording."""
    return TeachBackFlow(
        flow_runner or SequentialAiFlowRunner(),
        TeachBackFeedbackWriter(format_paise_as_whole_rupees),
    )


def render_weekly_template(
    language: MessageLanguage, facts: WeeklyMessageFacts
) -> WeeklyMessageText:
    """Renders the Layer 2 template message of one language: the fallback to expect."""
    return WeeklyMessageTemplate(format_paise_as_whole_rupees).render_in(language, facts)


def build_weekly_message_writer(
    clock: Clock, explanation_text: ExplanationTextPort | None = None
) -> AuditedWeeklyMessageWriter:
    """Builds the audited weekly writer; with no text port it always gives the template."""
    return AuditedWeeklyMessageWriter(
        build_weekly_message_flow(explanation_text),
        WeeklyMessageTemplate(format_paise_as_whole_rupees),
        build_weekly_message_cache(clock),
        AiUsageLogger(TEST_AI_PRICE_LIST),
    )
