"""Wire schema of GET .../receipt (C10): status, the frozen plan and the reference."""

from datetime import datetime
from typing import Annotated

from pydantic import Field

from emi_copilot.dtos.customer_consent_dtos import (
    PHONE_LAST_TWO_DIGITS_PATTERN,
    ConsentedPlanResponse,
)
from emi_copilot.dtos.wire_types import CamelCaseResponseModel
from emi_copilot.services.customer.consent_types import (
    CoolingOffNoticeStatus,
    CustomerReceipt,
    ReceiptStatus,
)


class CustomerReceiptResponse(CamelCaseResponseModel):
    """The receipt; READY_TO_PAY means the merchant now takes payment on Paytm.

    PAYMENT_PENDING, PAID and PAYMENT_NOT_COMPLETED follow the merchant's payment step; a
    payment that did not go through is worded as a next step, never as a refusal. There
    is no payment URL: the merchant performs the payment step (CLAUDE.md section 2, rule 9).
    coolingOffNoticeStatus PLACEHOLDER means the cooling-off wording awaits the lender's period.
    """

    status: ReceiptStatus
    reference: Annotated[str, Field(examples=["EMI-1511-0042"])]
    phone_last_two_digits: Annotated[
        str, Field(pattern=PHONE_LAST_TWO_DIGITS_PATTERN, examples=["42"])
    ]
    consented_at: Annotated[datetime, Field(examples=["2026-11-15T09:30:00Z"])]
    cooling_off_notice_status: CoolingOffNoticeStatus
    plan: ConsentedPlanResponse

    @classmethod
    def from_receipt(cls, receipt: CustomerReceipt) -> "CustomerReceiptResponse":
        """Converts the receipt, with the frozen plan in integer paise."""
        evidence = receipt.consent_record.evidence
        return cls(
            status=receipt.status,
            reference=evidence.consent_reference.value,
            phone_last_two_digits=evidence.phone_last_two_digits,
            consented_at=evidence.consented_at,
            cooling_off_notice_status=receipt.cooling_off_notice_status,
            plan=ConsentedPlanResponse.from_plan_snapshot(evidence.plan_snapshot),
        )
