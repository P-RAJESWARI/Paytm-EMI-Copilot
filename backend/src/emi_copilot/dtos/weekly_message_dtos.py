"""Wire schemas of the weekly message (M5 summary, M8): template text in English and Tamil."""

from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import Field

from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageText
from emi_copilot.dtos.wire_types import (
    CamelCaseQueryModel,
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
)
from emi_copilot.services.weekly_message_service import WeeklyMessageView

WEEK_START_DESCRIPTION = "The week's Monday (IST), as YYYY-MM-DD; a later week is refused."


class WeeklyMessageQuery(CamelCaseQueryModel):
    """Which week's message to read; the current week when left out."""

    period_start_date: Annotated[date | None, Field(description=WEEK_START_DESCRIPTION)] = None


class SendWeeklyMessageRequest(CamelCaseRequestBodyModel):
    """Which week's message to mark sent."""

    period_start_date: Annotated[
        date,
        Field(strict=False, description=WEEK_START_DESCRIPTION, examples=["2026-11-09"]),
    ]


class WeeklyMessageTextResponse(CamelCaseResponseModel):
    """One language's message: a title and its paragraphs (a left-out sentence is just absent)."""

    title: str
    paragraphs: list[str]

    @classmethod
    def from_text(cls, text: WeeklyMessageText) -> "WeeklyMessageTextResponse":
        """Builds the wire text."""
        return cls(title=text.title, paragraphs=list(text.paragraphs))


class WeeklyMessageLanguagesResponse(CamelCaseResponseModel):
    """The same message in English (en) and Tamil (ta, draft wording)."""

    en: WeeklyMessageTextResponse
    ta: WeeklyMessageTextResponse


class WeeklyMessageResponse(CamelCaseResponseModel):
    """A week's message; source TEMPLATE means deterministic text (Layer 4 may add AI text)."""

    period_start_date: date
    period_end_date: date
    source: Literal["TEMPLATE"]
    messages: WeeklyMessageLanguagesResponse
    is_sent: bool
    sent_at: datetime | None

    @classmethod
    def from_view(cls, view: WeeklyMessageView) -> "WeeklyMessageResponse":
        """Builds the wire message; sentAt is UTC to the second."""
        return cls(
            period_start_date=view.period.period_start_date,
            period_end_date=view.period.period_end_date,
            source="TEMPLATE",
            messages=WeeklyMessageLanguagesResponse(
                en=WeeklyMessageTextResponse.from_text(view.messages.english),
                ta=WeeklyMessageTextResponse.from_text(view.messages.tamil),
            ),
            is_sent=view.sent_at is not None,
            sent_at=(
                None
                if view.sent_at is None
                else view.sent_at.astimezone(UTC).replace(microsecond=0)
            ),
        )
