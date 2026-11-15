"""The weekly message wire schema: a source per language and an overall source."""

import pytest

from emi_copilot.domain.reports.weekly_message_template import WeeklyMessages, WeeklyMessageText
from emi_copilot.dtos.weekly_message_dtos import WeeklyMessageResponse
from emi_copilot.services.ai.ai_flow_types import AiTextSource
from emi_copilot.services.weekly_message_service import WeeklyMessageView
from tests.report_builders import build_design_weekly_message_facts

TEXT = WeeklyMessageText(title="Title", paragraphs=("Paragraph.",))


@pytest.mark.parametrize(
    ("english_source", "tamil_source", "expected_overall_source"),
    [
        (AiTextSource.TEMPLATE, AiTextSource.TEMPLATE, "TEMPLATE"),
        (AiTextSource.AI_AUDITED, AiTextSource.TEMPLATE, "AI_AUDITED"),
        (AiTextSource.TEMPLATE, AiTextSource.AI_AUDITED, "AI_AUDITED"),
    ],
)
def test_weekly_message_response_overall_source_is_ai_audited_when_any_language_is(
    english_source: AiTextSource, tamil_source: AiTextSource, expected_overall_source: str
) -> None:
    """Each language keeps its own source; the overall one says whether any text is AI."""
    view = WeeklyMessageView(
        period=build_design_weekly_message_facts().period,
        messages=WeeklyMessages(TEXT, TEXT),
        english_source=english_source,
        tamil_source=tamil_source,
        sent_at=None,
    )
    body = WeeklyMessageResponse.from_view(view).model_dump(mode="json", by_alias=True)
    assert body["source"] == expected_overall_source
    assert (body["messages"]["en"]["source"], body["messages"]["ta"]["source"]) == (
        english_source.value,
        tamil_source.value,
    )
