"""Inputs and results of consent (C9) and the receipt (C10), before they become wire DTOs."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from emi_copilot.domain.consent import ConsentRecord
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import InvalidConsentDataError
from emi_copilot.domain.money import Money


class CoolingOffNoticeStatus(StrEnum):
    """Whether the cooling-off wording is the lender's confirmed text or still a placeholder."""

    PLACEHOLDER = "PLACEHOLDER"


COOLING_OFF_WORDING_VERSION = CoolingOffNoticeStatus.PLACEHOLDER.value
"""The cooling-off wording version every consent records until the lender confirms the period."""


class ReceiptStatus(StrEnum):
    """Where the purchase stands on C10; a payment that did not go through explains the next step.

    READY_TO_PAY is the hand-off: the merchant now takes payment on Paytm. PAYMENT_PENDING means
    the merchant started a payment whose outcome is not known yet.
    """

    READY_TO_PAY = "READY_TO_PAY"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    PAYMENT_NOT_COMPLETED = "PAYMENT_NOT_COMPLETED"


@dataclass(frozen=True, slots=True)
class IssuedOtpChallenge:
    """Where the C9 code went (only the last two digits), when it ends, when it can be resent."""

    phone_last_two_digits: str
    expires_at: datetime
    resend_available_at: datetime
    attempts_remaining: int


@dataclass(frozen=True, slots=True)
class GiveConsentCommand:
    """Consent to one plan of the session's item, as shown on C9, with the code and the language.

    The selection is the offer id alone (ADR 0022 decision 1); the shown figures are the monthly
    amount and the total the customer saw, which a fresh quote must match. The code is kept out
    of repr and out of the request fingerprint.
    """

    idempotency_key: str
    offer_id: str
    shown_monthly_installment: Money
    shown_total_payable: Money
    otp_code: str = field(repr=False)
    has_agreed_to_plan: bool
    language: CustomerLanguage

    def __post_init__(self) -> None:
        """Rejects a consent the customer did not tick "I agree" for."""
        if self.has_agreed_to_plan is not True:
            raise InvalidConsentDataError("Consent needs the customer's agreement to the plan.")

    def calculate_request_fingerprint(self) -> str:
        """Gives the SHA-256 hex of the offer id and the shown figures; never the code or the key.

        An unsalted hash of a 6-digit code is effectively the code, so the code is left out: the
        same key and figures with another code is the same request (ADR 0021 decision 5).
        """
        canonical_body = json.dumps(
            {
                "offerId": self.offer_id,
                "shownMonthlyInstallmentInPaise": self.shown_monthly_installment.to_paise(),
                "shownTotalPayableInPaise": self.shown_total_payable.to_paise(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical_body.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CustomerReceipt:
    """What C10 shows: the status and the consent evidence (reference, plan, phone, language).

    There is no payment URL: the merchant performs the payment step on Paytm (rule 9).
    """

    status: ReceiptStatus
    consent_record: ConsentRecord
    cooling_off_notice_status: CoolingOffNoticeStatus
