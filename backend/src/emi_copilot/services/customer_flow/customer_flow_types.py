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
    """The customer's consent to one plan, with the one-time code, under an Idempotency-Key."""

    idempotency_key: str
    offer_id: str
    one_time_code: str

    def calculate_request_fingerprint(self) -> str:
        """Gives the SHA-256 hex of the canonical body; the key itself is not part of it."""
        canonical_body = json.dumps(
            {"offerId": self.offer_id, "otp": self.one_time_code},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical_body.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RecordedConsent:
    """Evidence of consent: the exact plan shown, frozen, with when and under which reference."""

    consent_id: str
    reference: str
    consented_at: datetime
    offer_snapshot: OfferSnapshot
    price: Money


@dataclass(frozen=True, slots=True)
class CustomerReceipt:
    """What C10 shows: status, the frozen plan, reference and the cooling-off note's status."""

    status: ReceiptStatus
    reference: str
    phone_last_two_digits: str
    consented_at: datetime
    cooling_off_notice_status: CoolingOffNoticeStatus
    offer_snapshot: OfferSnapshot
    price: Money
