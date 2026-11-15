"""The shop's weekly message (M5 "This week in short", M8): read it, or mark it sent once."""

from typing import Annotated

from fastapi import APIRouter, Body, Query

from emi_copilot.api.controllers.report_controller import GATEWAY_BACKED_REPORT_PROBLEMS
from emi_copilot.api.controllers.report_documentation import (
    INVALID_REPORTING_PERIOD_PROBLEM,
    SEND_WEEKLY_MESSAGE_REQUEST_EXAMPLE,
    WEEKLY_MESSAGE_EXAMPLE,
)
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.openapi_documentation import (
    MALFORMED_REQUEST_PROBLEM,
    MERCHANT_BEARER_NOTE,
    describe_problem_responses,
)
from emi_copilot.api.report_dependencies import WeeklyMessageServiceDependency
from emi_copilot.dtos.weekly_message_dtos import (
    SendWeeklyMessageRequest,
    WeeklyMessageQuery,
    WeeklyMessageResponse,
)

weekly_message_router = APIRouter(tags=["reports"])

TEMPLATE_NOTE = (
    "The text is written by the backend from the week's report numbers in English and draft "
    "Tamil. Each language is AI text whose every number passed the number audit (source "
    "AI_AUDITED) or the standard template text (TEMPLATE), used whenever AI is off, unavailable "
    "or fails the audit; a template sentence whose count is suppressed (1 to 4) is left out. "
    "The shown text is kept for a while, so a repeat read and send use exactly that text. "
)
SENT_WEEKLY_MESSAGE_EXAMPLE = {
    **WEEKLY_MESSAGE_EXAMPLE,
    "isSent": True,
    "sentAt": "2026-11-15T09:30:00Z",
}
WEEKLY_MESSAGE_PROBLEMS = (*GATEWAY_BACKED_REPORT_PROBLEMS, INVALID_REPORTING_PERIOD_PROBLEM)


@weekly_message_router.get(
    "/reports/weekly-message",
    summary="Read the shop's weekly message",
    description=(
        "The week's message (the current IST week when periodStartDate is left out), with "
        "whether it was sent. " + TEMPLATE_NOTE + MERCHANT_BEARER_NOTE
    ),
    response_description="The weekly message.",
    responses={
        200: {"content": {"application/json": {"example": WEEKLY_MESSAGE_EXAMPLE}}},
        **describe_problem_responses(*WEEKLY_MESSAGE_PROBLEMS),
    },
)
def get_weekly_message(
    weekly_message_query: Annotated[WeeklyMessageQuery, Query()],
    current_merchant: CurrentMerchant,
    weekly_message_service: WeeklyMessageServiceDependency,
) -> WeeklyMessageResponse:
    """Reads the signed-in shop's message for the week."""
    return WeeklyMessageResponse.from_view(
        weekly_message_service.get_weekly_message(
            current_merchant, weekly_message_query.period_start_date
        )
    )


@weekly_message_router.post(
    "/reports/weekly-message/send",
    summary="Mark the shop's weekly message sent",
    description=(
        "Marks the week's message sent once and hands it to the labelled "
        "MockWeeklyMessageDeliveryAdapter, which sends nothing (plan Q14, rule 10). Idempotent: "
        "a repeat answers 200 with the first sentAt and delivers nothing more. "
        + TEMPLATE_NOTE
        + MERCHANT_BEARER_NOTE
    ),
    response_description="The weekly message, now marked sent.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        **WEEKLY_MESSAGE_EXAMPLE,
                        "isSent": True,
                        "sentAt": "2026-11-15T09:30:00Z",
                    }
                }
            }
        },
        **describe_problem_responses(MALFORMED_REQUEST_PROBLEM, *WEEKLY_MESSAGE_PROBLEMS),
    },
)
def send_weekly_message(
    send_weekly_message_request: Annotated[
        SendWeeklyMessageRequest,
        Body(
            openapi_examples={
                "design-week": {
                    "summary": "The week of 9 November 2026",
                    "value": SEND_WEEKLY_MESSAGE_REQUEST_EXAMPLE,
                }
            }
        ),
    ],
    current_merchant: CurrentMerchant,
    weekly_message_service: WeeklyMessageServiceDependency,
) -> WeeklyMessageResponse:
    """Marks the signed-in shop's message for the week sent, once."""
    return WeeklyMessageResponse.from_view(
        weekly_message_service.send_weekly_message(
            current_merchant, send_weekly_message_request.period_start_date
        )
    )
