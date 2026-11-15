"""Wire schemas of the customer voice endpoints: transcription (C2, C8) and synthesis (C7)."""

from typing import Annotated

from pydantic import Field

from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    OpaqueIdentifier,
)
from emi_copilot.services.customer.customer_speech_service import SpeechTranscriptionResult


class SpeechTranscriptionResponse(CamelCaseResponseModel):
    """What was heard and the one amount in it; the budget is not changed by this answer.

    recognisedAmountInPaise is null when no single amount was heard. isLikelyMisheard asks the
    customer to check: no single amount, zero, or more each month than the item's price.
    """

    transcript: Annotated[str, Field(examples=["₹3,000 a month"])]
    recognised_amount_in_paise: Annotated[int | None, Field(examples=[300_000])]
    is_likely_misheard: Annotated[bool, Field(examples=[False])]

    @classmethod
    def from_result(cls, result: SpeechTranscriptionResult) -> "SpeechTranscriptionResponse":
        """Converts the transcription result."""
        return cls(
            transcript=result.transcript,
            recognised_amount_in_paise=result.recognised_amount_in_paise,
            is_likely_misheard=result.is_likely_misheard,
        )


class SpeechSynthesisRequest(CamelCaseRequestBodyModel):
    """Which shown explanation to speak; the client never supplies the text itself."""

    explanation_id: Annotated[OpaqueIdentifier, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0F"])]
