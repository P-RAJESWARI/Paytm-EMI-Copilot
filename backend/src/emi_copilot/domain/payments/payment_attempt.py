"""PaymentAttempt entity: one idempotent hand-off of a sale's amount to the payment gateway."""

import re
from dataclasses import dataclass
from datetime import datetime

from emi_copilot.domain.errors import InvalidPaymentAttemptError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_optional_non_empty_text,
    require_timezone_aware_moment,
    require_whole_paise_money,
)
from emi_copilot.domain.payments.offer_snapshot import OfferSnapshot
from emi_copilot.domain.payments.payment_attempt_status import PaymentAttemptStatus

# ADR 0005: the fingerprint is the SHA-256 of the canonical request body, as lowercase hex.
_REQUEST_FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class PaymentAttempt:
    """A stored attempt, identified by id and unique by order id and by idempotency key.

    It is immutable: a status or gateway-reference change produces a new instance (for example
    with dataclasses.replace) that the repository saves. Status transitions are not checked here.
    The gateway mode is the adapter name ("mock" or "paytm") that served the attempt.
    """

    id: str
    order_id: str
    idempotency_key: str
    request_fingerprint: str
    amount: Money
    status: PaymentAttemptStatus
    offer_snapshot: OfferSnapshot
    gateway_mode: str
    gateway_link_id: str | None
    payment_link_url: str | None
    gateway_transaction_id: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Rejects missing identifiers, a malformed fingerprint, a zero amount or bad timestamps."""
        for text, description in (
            (self.id, "payment attempt id"),
            (self.order_id, "order id"),
            (self.idempotency_key, "idempotency key"),
            (self.gateway_mode, "gateway mode"),
        ):
            require_non_empty_text(text, description, InvalidPaymentAttemptError)
        for optional_text, description in (
            (self.gateway_link_id, "gateway link id"),
            (self.payment_link_url, "payment link url"),
            (self.gateway_transaction_id, "gateway transaction id"),
        ):
            require_optional_non_empty_text(optional_text, description, InvalidPaymentAttemptError)
        self._require_valid_fingerprint()
        require_whole_paise_money(self.amount, "amount", InvalidPaymentAttemptError)
        if self.amount.is_zero:
            raise InvalidPaymentAttemptError("The amount must be above zero rupees.")
        if not isinstance(self.status, PaymentAttemptStatus):
            raise InvalidPaymentAttemptError("The status must be a PaymentAttemptStatus.")
        if not isinstance(self.offer_snapshot, OfferSnapshot):
            raise InvalidPaymentAttemptError("The offer snapshot must be an OfferSnapshot.")
        self._require_valid_timestamps()

    def _require_valid_fingerprint(self) -> None:
        """Raises unless the request fingerprint is 64 lowercase hexadecimal characters."""
        if (
            not isinstance(self.request_fingerprint, str)
            or _REQUEST_FINGERPRINT_PATTERN.fullmatch(self.request_fingerprint) is None
        ):
            raise InvalidPaymentAttemptError(
                "The request fingerprint must be a lowercase hex SHA-256 digest."
            )

    def _require_valid_timestamps(self) -> None:
        """Raises unless both timestamps are aware and the update is not before creation."""
        require_timezone_aware_moment(self.created_at, "created at", InvalidPaymentAttemptError)
        require_timezone_aware_moment(self.updated_at, "updated at", InvalidPaymentAttemptError)
        if self.updated_at < self.created_at:
            raise InvalidPaymentAttemptError("The updated at moment cannot be before created at.")
