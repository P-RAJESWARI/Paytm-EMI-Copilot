"""Typed domain errors; each carries a stable machine-readable code for problem+json responses."""

from enum import StrEnum
from typing import ClassVar


class DomainError(Exception):
    """Base class for every business-rule violation raised by domain code."""

    code: ClassVar[str] = "DOMAIN_ERROR"

    def __init__(self, detail: str) -> None:
        """Stores an English, developer-facing explanation that never contains personal data."""
        super().__init__(detail)
        self.detail = detail


class InvalidMoneyAmountError(DomainError):
    """Raised when a value cannot be, or cannot become, a valid Money amount."""

    code: ClassVar[str] = "INVALID_MONEY_AMOUNT"


class InvalidEmiTermsError(DomainError):
    """Raised when EMI inputs are unusable, so no schedule can even be attempted.

    Examples: a principal that is zero, not Money or not whole paise; a tenure below one month; a
    negative, non-finite or non-Decimal rate; a quoted extra that is not whole-paise Money.
    """

    code: ClassVar[str] = "INVALID_EMI_TERMS"


class EmiScheduleNotRepresentableError(DomainError):
    """Raised when valid terms cannot give non-negative whole-paise installments.

    This happens only for tiny amounts over long tenures, where the n - 1 rounded regular
    installments already exceed the total, so the last installment would have to be negative.
    """

    code: ClassVar[str] = "EMI_SCHEDULE_NOT_REPRESENTABLE"


class InvalidOfferSnapshotError(DomainError):
    """Raised when a frozen offer snapshot is incomplete, inconsistent or cannot be decoded."""

    code: ClassVar[str] = "INVALID_OFFER_SNAPSHOT"


class InvalidPaymentAttemptError(DomainError):
    """Raised when a payment attempt would be built with missing or inconsistent fields."""

    code: ClassVar[str] = "INVALID_PAYMENT_ATTEMPT"


class InvalidAuditEventError(DomainError):
    """Raised when an audit event would be built with missing fields or non-scalar details."""

    code: ClassVar[str] = "INVALID_AUDIT_EVENT"


class PaymentAttemptAlreadyExistsError(DomainError):
    """Raised when a payment attempt with the same id, order id or idempotency key is stored.

    Two requests racing with one Idempotency-Key both pass the lookup; the database unique
    constraint stops the second, and this error lets the service re-read the stored attempt.
    """

    code: ClassVar[str] = "PAYMENT_ATTEMPT_ALREADY_EXISTS"


class PaymentAttemptNotFoundError(DomainError):
    """Raised when a payment attempt that must already be stored cannot be found."""

    code: ClassVar[str] = "PAYMENT_ATTEMPT_NOT_FOUND"


class InvalidPaymentGatewayValueError(DomainError):
    """Raised when a value passed to or returned by the payment gateway port is incomplete.

    Examples: a blank product id in an offer query, a no-cost offer quoted with an extra cost, or a
    paid status result without the amount paid. It is a bad value, not a failed gateway call.
    """

    code: ClassVar[str] = "INVALID_PAYMENT_GATEWAY_VALUE"


class PaymentGatewayError(DomainError):
    """Base class for a payment gateway call that failed; adapters raise only its subclasses.

    Adapters translate every vendor failure into one of these at the boundary, so a raw vendor
    payload, status code or message never reaches a service (backend.md section 6).
    """

    code: ClassVar[str] = "PAYMENT_GATEWAY_ERROR"


class PaymentGatewayTimeoutError(PaymentGatewayError):
    """Raised when the gateway did not answer within the configured timeout.

    On a create-link call the outcome is unknown: the gateway may or may not have made the link,
    so the call is never retried and the attempt is stored as OUTCOME_UNKNOWN (ADR 0005).
    """

    code: ClassVar[str] = "PAYMENT_GATEWAY_TIMEOUT"


class PaymentGatewayUnavailableError(PaymentGatewayError):
    """Raised when the gateway cannot serve a call: the circuit breaker is open or it failed itself.

    With the breaker open nothing was sent. A server error from the gateway (5xx) is reported here
    too, after any retries an idempotent call is allowed.
    """

    code: ClassVar[str] = "PAYMENT_GATEWAY_UNAVAILABLE"


class PaymentGatewayRejectionReason(StrEnum):
    """Why the gateway refused a request, in our own stable words; adapters map vendor codes."""

    INVALID_REQUEST = "INVALID_REQUEST"
    """The gateway found a field of the request invalid, for example an amount out of range."""

    DUPLICATE_ORDER_ID = "DUPLICATE_ORDER_ID"
    """The gateway already holds a payment link or transaction for this order id."""

    OPERATION_NOT_PERMITTED = "OPERATION_NOT_PERMITTED"
    """The merchant account is not allowed to do this, for example EMI is not enabled for it."""

    GATEWAY_INTERNAL_ERROR = "GATEWAY_INTERNAL_ERROR"
    """The gateway answered that it failed on its own side (ADR 0011); our request may be fine.

    A new attempt needs a new idempotency key and could, rarely, make a second payment link.
    """


class PaymentGatewayRequestRejectedError(PaymentGatewayError):
    """Raised when the gateway answered that it did not do what was asked, giving a reason.

    For most reasons the same request would be refused again. GATEWAY_INTERNAL_ERROR means the
    gateway failed on its own side; the request may be fine, but a new create-link attempt needs
    a new idempotency key (ADR 0011). It carries a stable domain reason only, never the vendor's
    code, message or payload.
    """

    code: ClassVar[str] = "PAYMENT_GATEWAY_REQUEST_REJECTED"

    def __init__(self, reason: PaymentGatewayRejectionReason, detail: str) -> None:
        """Stores the stable rejection reason with an English, developer-facing explanation."""
        super().__init__(detail)
        self.reason = reason


class WebhookSignatureInvalidError(DomainError):
    """Raised when a received webhook's signature is missing or does not match its fields.

    It is raised before any field of the notification is trusted; the API answers 401 and an audit
    event is written (api-conventions.md section 8, ADR 0002).
    """

    code: ClassVar[str] = "WEBHOOK_SIGNATURE_INVALID"


class OfferNotFoundError(DomainError):
    """Raised when a chosen offer id is not among the offers the gateway quotes for the item."""

    code: ClassVar[str] = "OFFER_NOT_FOUND"


class IdempotencyKeyReusedError(DomainError):
    """Raised when an Idempotency-Key is replayed with a different request body (ADR 0005)."""

    code: ClassVar[str] = "IDEMPOTENCY_KEY_REUSED"


class PaymentLinkOutcomeUnknownError(DomainError):
    """Raised when a key is replayed whose create-link call timed out with an unknown outcome.

    Nothing is re-sent silently; the caller must start again with a new Idempotency-Key (ADR 0005).
    """

    code: ClassVar[str] = "PAYMENT_LINK_OUTCOME_UNKNOWN"
