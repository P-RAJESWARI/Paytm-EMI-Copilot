"""Inputs and results of the customer flow services (C1 to C10), before they become wire DTOs."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferSnapshot


class ComfortCheckStatus(StrEnum):
    """Whether the customer let the comfort check run (C3); skipping is always allowed."""

    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class ReceiptStatus(StrEnum):
    """Where the purchase stands on the receipt (C10); a failed payment explains the next step.

    READY_TO_PAY is the hand-off state: the merchant now takes payment on Paytm. The other
    states arrive with payment status in Phase 3C.
    """

    READY_TO_PAY = "READY_TO_PAY"
    PAID = "PAID"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_NOT_COMPLETED = "PAYMENT_NOT_COMPLETED"


class CoolingOffNoticeStatus(StrEnum):
    """Whether the cooling-off wording is the lender's confirmed text or still a placeholder."""

    PLACEHOLDER = "PLACEHOLDER"


@dataclass(frozen=True, slots=True)
class CustomerSessionCredentials:
    """The session id from the path and the token from the X-Customer-Session-Token header."""

    customer_session_id: str
    session_token: str


@dataclass(frozen=True, slots=True)
class StartedCustomerSession:
    """What C1 shows after the QR is scanned, with the token for every later call."""

    customer_session_id: str
    session_token: str
    session_code: str
    shop_name: str
    product_name: str
    price: Money
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ComfortCheckOutcome:
    """The C3 answer: completed with the synthetic profile read, or skipped with none read."""

    status: ComfortCheckStatus
    is_synthetic_data: bool
    financial_profile: FinancialProfile | None


@dataclass(frozen=True, slots=True)
class OtpChallenge:
    """The C9 one-time code request: where it went, when it ends and when it can be re-sent."""

    phone_last_two_digits: str
    expires_at: datetime
    resend_available_at: datetime


@dataclass(frozen=True, slots=True)
class GiveConsentCommand:
    """Consent to the exact selection shown on C9, with the one-time code, under a key.

    The selection is the offer, the product (None means the session's item) and the down payment
    (zero for none). The shown figures are what the customer saw; a fresh quote must match them.
    """

    idempotency_key: str
    offer_id: str
    one_time_code: str
    product_id: str | None
    down_payment: Money
    shown_monthly_installment: Money
    shown_total_payable: Money

    def calculate_request_fingerprint(self) -> str:
        """Gives the SHA-256 hex of the selection and shown figures; never the code or the key.

        An unsalted hash of a 6-digit code is effectively the code, so the code is left out: the
        same key and selection with another code is the same request (ADR 0021).
        """
        canonical_body = json.dumps(
            {
                "offerId": self.offer_id,
                "productId": self.product_id,
                "downPaymentInPaise": self.down_payment.to_paise(),
                "shownMonthlyInstallmentInPaise": self.shown_monthly_installment.to_paise(),
                "shownTotalPayableInPaise": self.shown_total_payable.to_paise(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical_body.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ConsentedPlan:
    """The exact selection agreed to: the plan snapshot plus product, price and down payment.

    financed_amount is what the plan spreads over its months (the price less the down payment);
    it equals the snapshot's principal.
    """

    offer_snapshot: OfferSnapshot
    product_id: str
    product_name: str
    price: Money
    down_payment: Money
    financed_amount: Money


@dataclass(frozen=True, slots=True)
class RecordedConsent:
    """Evidence of consent: the exact selection shown, frozen, with when and which reference."""

    consent_id: str
    reference: str
    consented_at: datetime
    consented_plan: ConsentedPlan


@dataclass(frozen=True, slots=True)
class CustomerReceipt:
    """What C10 shows: status, the frozen selection, reference and the cooling-off note's status."""

    status: ReceiptStatus
    reference: str
    phone_last_two_digits: str
    consented_at: datetime
    cooling_off_notice_status: CoolingOffNoticeStatus
    consented_plan: ConsentedPlan
