"""Wire schemas of POST .../teach-back (C8): the customer's own words and advisory feedback."""

from typing import Annotated

from pydantic import Field, StringConstraints

from emi_copilot.domain.teach_back import TeachBackResult
from emi_copilot.dtos.customer_explanation_dtos import HighlightedAmountResponse
from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    OpaqueIdentifier,
)
from emi_copilot.services.customer.customer_teach_back_service import TeachBackOutcome

MAXIMUM_ANSWER_LENGTH = 500


class TeachBackRequest(CamelCaseRequestBodyModel):
    """The plan and the customer's answer in their own words (typed or transcribed)."""

    offer_id: Annotated[OpaqueIdentifier, Field(examples=["mock-offer-no-cost-6m"])]
    answer_text: Annotated[
        str,
        StringConstraints(min_length=1, max_length=MAXIMUM_ANSWER_LENGTH),
        Field(examples=["3,667 every month for 6 months, nothing extra"]),
    ]


class TeachBackResponse(CamelCaseResponseModel):
    """Advisory feedback: CLOSE_ENOUGH or TRY_AGAIN, with the plan's terms restated.

    heardText echoes the monthly amount heard (null when none); highlightedAmounts are the
    engine's figures. Nothing is stored and consent is never blocked.
    """

    result: TeachBackResult
    title: Annotated[str, Field(examples=["Nearly there"])]
    body: Annotated[
        str,
        Field(
            examples=[
                "You will pay ₹3,667 every month for 6 months. Nothing extra on top of ₹22,000."
            ]
        ),
    ]
    heard_text: Annotated[str | None, Field(examples=["About ₹3,667 every month"])]
    highlighted_amounts: list[HighlightedAmountResponse]

    @classmethod
    def from_outcome(cls, outcome: TeachBackOutcome) -> "TeachBackResponse":
        """Converts the feedback card and the engine's highlighted figures."""
        feedback = outcome.feedback
        return cls(
            result=feedback.result,
            title=feedback.title,
            body=feedback.body,
            heard_text=feedback.heard_text,
            highlighted_amounts=[
                HighlightedAmountResponse.from_highlighted_amount(highlighted_amount)
                for highlighted_amount in outcome.highlighted_amounts
            ],
        )
