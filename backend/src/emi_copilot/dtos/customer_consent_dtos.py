"""Wire schemas of the C9 one-time code and POST .../consent (consent as evidence)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from emi_copilot.domain.consent import ConsentPlanSnapshot, ConsentRecord
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    OpaqueIdentifier,
    PositiveAmountInPaise,
)
from emi_copilot.services.customer.consent_types import (
    GiveConsentCommand,
    IssuedOtpChallenge,
    ReceiptStatus,
    rebuild_agreed_schedule,
)

PHONE_LAST_TWO_DIGITS_PATTERN = r"^[0-9]{2}$"
ONE_TIME_CODE_PATTERN = r"^[0-9]{6}$"
EXAMPLE_PRODUCT_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0F"


class OtpChallengeResponse(CamelCaseResponseModel):
    """Where the code went (only the last two digits), when it ends, resends and how many tries."""

    phone_last_two_digits: Annotated[
        str, Field(pattern=PHONE_LAST_TWO_DIGITS_PATTERN, examples=["42"])
    ]
    expires_at: Annotated[datetime, Field(examples=["2026-11-15T09:35:00Z"])]
    resend_available_at: Annotated[datetime, Field(examples=["2026-11-15T09:30:30Z"])]
    attempts_remaining: Annotated[int, Field(ge=1, examples=[3])]

    @classmethod
    def from_challenge(cls, challenge: IssuedOtpChallenge) -> "OtpChallengeResponse":
        """Converts the issued challenge for the wire."""
        return cls(
            phone_last_two_digits=challenge.phone_last_two_digits,
            expires_at=challenge.expires_at,
            resend_available_at=challenge.resend_available_at,
            attempts_remaining=challenge.attempts_remaining,
        )


class GiveConsentRequest(CamelCaseRequestBodyModel):
    """The plan agreed to, the figures C9 showed for it, the 6-digit code and the agreement.

    The plan is an offer on the session's item at the sale price (ADR 0022 decision 1). It is
    re-quoted server-side; if the shown monthly or total no longer match, the answer is 409
    SHOWN_PLAN_CHANGED and nothing is recorded.
    """

    offer_id: Annotated[OpaqueIdentifier, Field(examples=["mock-offer-no-cost-6m"])]
    shown_monthly_installment_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[366_667])]
    shown_total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    otp: Annotated[str, Field(pattern=ONE_TIME_CODE_PATTERN, examples=["123456"])]
    has_agreed_to_plan: Annotated[Literal[True], Field(examples=[True])]

    def to_command(self, idempotency_key: str, language: CustomerLanguage) -> GiveConsentCommand:
        """Gives the service command for this body, the caller's key and the customer's language."""
        return GiveConsentCommand(
            idempotency_key=idempotency_key,
            offer_id=self.offer_id,
            shown_monthly_installment=Money.from_paise(self.shown_monthly_installment_in_paise),
            shown_total_payable=Money.from_paise(self.shown_total_payable_in_paise),
            otp_code=self.otp,
            has_agreed_to_plan=self.has_agreed_to_plan,
            language=language,
        )


class ConsentedPlanResponse(CamelCaseResponseModel):
    """The frozen plan: tenure - 1 regular installments then a last, totals, product and price.

    The installments are our exact schedule, so they add up to totalPayableInPaise to the paisa.
    There is no down payment in this build (ADR 0022 decision 1): downPaymentInPaise is 0 and
    financedAmountInPaise equals priceInPaise.
    """

    offer_id: Annotated[str, Field(examples=["mock-offer-no-cost-6m"])]
    lender_label: Annotated[str, Field(examples=["Brand"])]
    emi_type: EmiType
    tenure_in_months: Annotated[int, Field(ge=1, examples=[6])]
    regular_installment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[366_667])]
    last_installment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[366_665])]
    extra_in_total_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[0])]
    total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    product_id: Annotated[str, Field(examples=[EXAMPLE_PRODUCT_ID])]
    product_name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    down_payment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[0])]
    financed_amount_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]

    @classmethod
    def from_plan_snapshot(cls, plan_snapshot: ConsentPlanSnapshot) -> "ConsentedPlanResponse":
        """Converts the frozen evidence, with its installments rebuilt exactly, to integer paise."""
        chosen_plan = plan_snapshot.chosen_plan
        schedule = rebuild_agreed_schedule(plan_snapshot)
        return cls(
            offer_id=chosen_plan.offer_id,
            lender_label=chosen_plan.lender_label,
            emi_type=chosen_plan.plan_kind,
            tenure_in_months=chosen_plan.tenure_in_months,
            regular_installment_in_paise=schedule.regular_installment.to_paise(),
            last_installment_in_paise=schedule.last_installment.to_paise(),
            extra_in_total_in_paise=chosen_plan.extra_in_total.to_paise(),
            total_payable_in_paise=chosen_plan.total_payable.to_paise(),
            price_in_paise=plan_snapshot.price.to_paise(),
            product_id=plan_snapshot.product_id,
            product_name=plan_snapshot.product_name,
            down_payment_in_paise=0,
            financed_amount_in_paise=plan_snapshot.price.to_paise(),
        )


class ConsentResponse(CamelCaseResponseModel):
    """The recorded consent: the exact plan agreed to, frozen, and the hand-off status."""

    consent_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0D"])]
    reference: Annotated[str, Field(examples=["EMI-1511-0042"])]
    consented_at: Annotated[datetime, Field(examples=["2026-11-15T09:30:00Z"])]
    status: ReceiptStatus
    plan: ConsentedPlanResponse

    @classmethod
    def from_consent_record(cls, record: ConsentRecord) -> "ConsentResponse":
        """Converts the record; a replay converts to the same body, always READY_TO_PAY."""
        evidence = record.evidence
        return cls(
            consent_id=evidence.consent_id,
            reference=evidence.consent_reference.value,
            consented_at=evidence.consented_at,
            status=ReceiptStatus.READY_TO_PAY,
            plan=ConsentedPlanResponse.from_plan_snapshot(evidence.plan_snapshot),
        )
