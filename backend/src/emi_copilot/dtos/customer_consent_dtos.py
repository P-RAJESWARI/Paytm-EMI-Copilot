"""Wire schemas of the C9 one-time code and POST .../consent (consent as evidence)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from emi_copilot.dtos.payment_link_dtos import OfferSnapshotResponse
from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    OpaqueIdentifier,
)
from emi_copilot.services.customer_flow.customer_flow_types import (
    GiveConsentCommand,
    OtpChallenge,
    ReceiptStatus,
    RecordedConsent,
)

PHONE_LAST_TWO_DIGITS_PATTERN = r"^[0-9]{2}$"
ONE_TIME_CODE_PATTERN = r"^[0-9]{6}$"


class OtpChallengeResponse(CamelCaseResponseModel):
    """Where the code went (only the last two digits) and when it ends or can be re-sent."""

    phone_last_two_digits: Annotated[
        str, Field(pattern=PHONE_LAST_TWO_DIGITS_PATTERN, examples=["42"])
    ]
    expires_at: Annotated[datetime, Field(examples=["2026-11-15T09:35:00Z"])]
    resend_available_at: Annotated[datetime, Field(examples=["2026-11-15T09:30:30Z"])]

    @classmethod
    def from_challenge(cls, challenge: OtpChallenge) -> "OtpChallengeResponse":
        """Converts the challenge for the wire."""
        return cls(
            phone_last_two_digits=challenge.phone_last_two_digits,
            expires_at=challenge.expires_at,
            resend_available_at=challenge.resend_available_at,
        )


class GiveConsentRequest(CamelCaseRequestBodyModel):
    """The plan agreed to, the 6-digit code and the customer's explicit agreement.

    Every figure of the plan is re-quoted server-side; only the offer id is taken from here.
    """

    offer_id: Annotated[OpaqueIdentifier, Field(examples=["mock-offer-no-cost-6m"])]
    otp: Annotated[str, Field(pattern=ONE_TIME_CODE_PATTERN, examples=["123456"])]
    has_agreed_to_plan: Annotated[Literal[True], Field(examples=[True])]

    def to_command(self, idempotency_key: str) -> GiveConsentCommand:
        """Gives the service command for this body under the caller's Idempotency-Key."""
        return GiveConsentCommand(
            idempotency_key=idempotency_key, offer_id=self.offer_id, one_time_code=self.otp
        )


class ConsentResponse(CamelCaseResponseModel):
    """The recorded consent: the exact plan agreed to, frozen, and the hand-off status."""

    consent_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0D"])]
    reference: Annotated[str, Field(examples=["EMI-2611-0042"])]
    consented_at: Annotated[datetime, Field(examples=["2026-11-15T09:31:00Z"])]
    status: ReceiptStatus
    plan: OfferSnapshotResponse

    @classmethod
    def from_recorded_consent(cls, recorded_consent: RecordedConsent) -> "ConsentResponse":
        """Converts the recorded consent; a replay converts to the same body."""
        return cls(
            consent_id=recorded_consent.consent_id,
            reference=recorded_consent.reference,
            consented_at=recorded_consent.consented_at,
            status=ReceiptStatus.READY_TO_PAY,
            plan=OfferSnapshotResponse.from_snapshot(
                recorded_consent.offer_snapshot, recorded_consent.price
            ),
        )
