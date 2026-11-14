"""Wire schema of GET .../receipt (C10): status, the frozen plan and the reference."""

from datetime import datetime
from typing import Annotated

from pydantic import Field

from emi_copilot.dtos.customer_consent_dtos import PHONE_LAST_TWO_DIGITS_PATTERN
from emi_copilot.dtos.payment_link_dtos import OfferSnapshotResponse
from emi_copilot.dtos.wire_types import CamelCaseResponseModel
from emi_copilot.services.customer_flow.customer_flow_types import (
    CoolingOffNoticeStatus,
    CustomerReceipt,
    ReceiptStatus,
)


class CustomerReceiptResponse(CamelCaseResponseModel):
    """The receipt; READY_TO_PAY means the merchant now takes payment on Paytm.

    There is no payment URL: the merchant performs the payment step (CLAUDE.md section 2, rule 9).
    coolingOffNoticeStatus PLACEHOLDER means the cooling-off wording awaits the lender's period.
    """

    status: ReceiptStatus
    reference: Annotated[str, Field(examples=["EMI-2611-0042"])]
    phone_last_two_digits: Annotated[
        str, Field(pattern=PHONE_LAST_TWO_DIGITS_PATTERN, examples=["42"])
    ]
    consented_at: Annotated[datetime, Field(examples=["2026-11-15T09:31:00Z"])]
    cooling_off_notice_status: CoolingOffNoticeStatus
    plan: OfferSnapshotResponse

    @classmethod
    def from_receipt(cls, receipt: CustomerReceipt) -> "CustomerReceiptResponse":
        """Converts the receipt, with the plan in integer paise."""
        return cls(
            status=receipt.status,
            reference=receipt.reference,
            phone_last_two_digits=receipt.phone_last_two_digits,
            consented_at=receipt.consented_at,
            cooling_off_notice_status=receipt.cooling_off_notice_status,
            plan=OfferSnapshotResponse.from_snapshot(receipt.offer_snapshot, receipt.price),
        )
