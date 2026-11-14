"""Wire schemas of the C9 one-time code and POST .../consent (consent as evidence)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from emi_copilot.domain.money import Money
from emi_copilot.dtos.payment_link_dtos import OfferSnapshotResponse
from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    OpaqueIdentifier,
    PositiveAmountInPaise,
)
from emi_copilot.services.customer_flow.customer_flow_types import (
    ConsentedPlan,
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
    """The exact selection agreed to, the figures shown, the 6-digit code and the agreement.

    The selection is the offer, the product (null for the session's item, or a cheaper model
    from the alternatives) and the down payment (0 for none, else exactly the one suggested).
    It is re-quoted server-side; if the shown monthly or total no longer match, the answer is
    409 SHOWN_PLAN_CHANGED and nothing is recorded (ADR 0021).
    """

    offer_id: Annotated[OpaqueIdentifier, Field(examples=["mock-offer-no-cost-6m"])]
    product_id: Annotated[OpaqueIdentifier | None, Field(examples=[None])] = None
    down_payment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[0])] = 0
    shown_monthly_installment_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[366_667])]
    shown_total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    otp: Annotated[str, Field(pattern=ONE_TIME_CODE_PATTERN, examples=["123456"])]
    has_agreed_to_plan: Annotated[Literal[True], Field(examples=[True])]

    def to_command(self, idempotency_key: str) -> GiveConsentCommand:
        """Gives the service command for this body under the caller's Idempotency-Key."""
        return GiveConsentCommand(
            idempotency_key=idempotency_key,
            offer_id=self.offer_id,
            one_time_code=self.otp,
            product_id=self.product_id,
            down_payment=Money.from_paise(self.down_payment_in_paise),
            shown_monthly_installment=Money.from_paise(self.shown_monthly_installment_in_paise),
            shown_total_payable=Money.from_paise(self.shown_total_payable_in_paise),
        )


class ConsentedPlanResponse(OfferSnapshotResponse):
    """The frozen selection: the plan's schedule plus product, price and down payment.

    priceInPaise is the product's price; financedAmountInPaise is the price less the down
    payment, which the installments repay with any extra.
    """

    product_id: Annotated[str, Field(examples=["stub-product-phone-128gb"])]
    product_name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    down_payment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[0])]
    financed_amount_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]

    @classmethod
    def from_consented_plan(cls, consented_plan: ConsentedPlan) -> "ConsentedPlanResponse":
        """Converts the frozen selection to integer paise for the wire."""
        snapshot_fields = OfferSnapshotResponse.from_snapshot(
            consented_plan.offer_snapshot, consented_plan.price
        ).model_dump()
        return cls(
            **snapshot_fields,
            product_id=consented_plan.product_id,
            product_name=consented_plan.product_name,
            down_payment_in_paise=consented_plan.down_payment.to_paise(),
            financed_amount_in_paise=consented_plan.financed_amount.to_paise(),
        )


class ConsentResponse(CamelCaseResponseModel):
    """The recorded consent: the exact plan agreed to, frozen, and the hand-off status."""

    consent_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0D"])]
    reference: Annotated[str, Field(examples=["EMI-2611-0042"])]
    consented_at: Annotated[datetime, Field(examples=["2026-11-15T09:31:00Z"])]
    status: ReceiptStatus
    plan: ConsentedPlanResponse

    @classmethod
    def from_recorded_consent(cls, recorded_consent: RecordedConsent) -> "ConsentResponse":
        """Converts the recorded consent; a replay converts to the same body."""
        return cls(
            consent_id=recorded_consent.consent_id,
            reference=recorded_consent.reference,
            consented_at=recorded_consent.consented_at,
            status=ReceiptStatus.READY_TO_PAY,
            plan=ConsentedPlanResponse.from_consented_plan(recorded_consent.consented_plan),
        )
