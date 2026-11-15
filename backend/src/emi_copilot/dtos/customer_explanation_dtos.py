"""Wire schemas of POST .../explanation (C7): plain words about one plan and its two figures."""

from typing import Annotated

from pydantic import Field

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    OpaqueIdentifier,
)
from emi_copilot.services.ai.shown_explanation_cache import ShownExplanation
from emi_copilot.services.customer.explanation_types import (
    ExplanationSource,
    HighlightedAmount,
    HighlightedAmountKind,
)


class PlanExplanationRequest(CamelCaseRequestBodyModel):
    """The plan the customer wants explained; the language comes from Accept-Language."""

    offer_id: Annotated[OpaqueIdentifier, Field(examples=["mock-offer-no-cost-6m"])]


class HighlightedAmountResponse(CamelCaseResponseModel):
    """One figure the text mentions, exactly as the engine computed it, in integer paise."""

    kind: HighlightedAmountKind
    amount_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[366_667])]

    @classmethod
    def from_highlighted_amount(
        cls, highlighted_amount: HighlightedAmount
    ) -> "HighlightedAmountResponse":
        """Converts one highlighted amount to integer paise."""
        return cls(
            kind=highlighted_amount.kind, amount_in_paise=highlighted_amount.amount.to_paise()
        )


class PlanExplanationResponse(CamelCaseResponseModel):
    """The explanation text and the figures it mentions; source TEMPLATE is the standard text.

    source AI_AUDITED is AI text whose every number passed the number audit. Every rupee amount
    in the text is one of highlightedAmounts, shown in whole rupees. explanationId names this
    shown text for speech synthesis.
    """

    explanation_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0F"])]
    text: Annotated[
        str,
        Field(
            examples=[
                "No-cost EMI: you pay ₹3,667 each month for 6 months. The extra you pay in "
                "total is ₹0, so nothing is added to the price."
            ]
        ),
    ]
    language: CustomerLanguage
    source: ExplanationSource
    highlighted_amounts: list[HighlightedAmountResponse]

    @classmethod
    def from_shown_explanation(cls, shown: ShownExplanation) -> "PlanExplanationResponse":
        """Converts the shown explanation, keeping the order of its highlighted amounts."""
        explanation = shown.explanation
        return cls(
            explanation_id=shown.explanation_id,
            text=explanation.text,
            language=explanation.language,
            source=explanation.source,
            highlighted_amounts=[
                HighlightedAmountResponse.from_highlighted_amount(highlighted_amount)
                for highlighted_amount in explanation.highlighted_amounts
            ],
        )
