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


class PaymentLinkFailureCode(StrEnum):
    """Why a create-link call ended with no link; stored on a LINK_CREATION_FAILED attempt.

    Stored by value, so a rename or a new member needs a migration. GATEWAY_UNAVAILABLE means the
    request provably never left (ADR 0010 section 3); every other code is the gateway's refusal
    reason, named exactly as in PaymentGatewayRejectionReason.
    """

    GATEWAY_UNAVAILABLE = "GATEWAY_UNAVAILABLE"
    INVALID_REQUEST = "INVALID_REQUEST"
    DUPLICATE_ORDER_ID = "DUPLICATE_ORDER_ID"
    OPERATION_NOT_PERMITTED = "OPERATION_NOT_PERMITTED"
    GATEWAY_INTERNAL_ERROR = "GATEWAY_INTERNAL_ERROR"


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


class PaymentLinkCreationFailedError(DomainError):
    """Raised when a key is replayed whose create-link call certainly made no link.

    It carries the stored failure code. Nothing is re-sent; the caller must start again with a
    new Idempotency-Key, as for an unknown outcome (ADR 0005).
    """

    code: ClassVar[str] = "PAYMENT_LINK_CREATION_FAILED"

    def __init__(self, failure_code: PaymentLinkFailureCode, detail: str) -> None:
        """Stores the failure code recorded on the attempt with an English explanation."""
        super().__init__(detail)
        self.failure_code = failure_code


class PaymentLinkCreationInProgressError(DomainError):
    """Raised when a key is replayed while its first create-link call has not finished yet.

    The first request owns the attempt; the caller may replay the same key once it has finished.
    """

    code: ClassVar[str] = "PAYMENT_LINK_CREATION_IN_PROGRESS"


class InvalidMerchantDataError(DomainError):
    """Raised when a merchant, device pairing or catalogue product would be built incomplete."""

    code: ClassVar[str] = "INVALID_MERCHANT_DATA"


class InvalidPairingCredentialsError(DomainError):
    """Raised when a shop id and PIN do not pair a device.

    An unknown shop and a wrong PIN raise this same error with the same detail, so a caller
    cannot learn which shop ids exist.
    """

    code: ClassVar[str] = "INVALID_PAIRING_CREDENTIALS"


class RetryLaterError(DomainError):
    """Base class for a refusal that ends by itself; it says how many seconds to wait."""

    code: ClassVar[str] = "RETRY_LATER"

    def __init__(self, retry_after_in_seconds: int, detail: str) -> None:
        """Stores the whole seconds to wait, at least one, with an English explanation."""
        if isinstance(retry_after_in_seconds, bool) or retry_after_in_seconds < 1:
            raise ValueError("A retry delay is a whole number of seconds, at least one.")
        super().__init__(detail)
        self.retry_after_in_seconds = retry_after_in_seconds


class PairingTemporarilyLockedError(RetryLaterError):
    """Raised while a shop is locked after repeated wrong PINs; even the right PIN is refused."""

    code: ClassVar[str] = "PAIRING_TEMPORARILY_LOCKED"


class RequestRateLimitedError(RetryLaterError):
    """Raised when one client has sent too many requests of one kind in the current window."""

    code: ClassVar[str] = "RATE_LIMITED"


class MerchantAuthenticationRequiredError(DomainError):
    """Raised when a merchant endpoint gets a missing, unknown, expired or revoked bearer token.

    The reasons are not told apart, so a probe learns nothing from the answer.
    """

    code: ClassVar[str] = "MERCHANT_AUTHENTICATION_REQUIRED"


class ProductNotFoundError(DomainError):
    """Raised when a product id is not in the signed-in merchant's catalogue.

    Another merchant's product raises this too, so its existence stays hidden (404).
    """

    code: ClassVar[str] = "PRODUCT_NOT_FOUND"


class InvalidSaleDataError(DomainError):
    """Raised when a sale, its chosen plan, session code or funnel event would be inconsistent."""

    code: ClassVar[str] = "INVALID_SALE_DATA"


class SaleNotFoundError(DomainError):
    """Raised when a sale id is not one of the signed-in merchant's sales.

    Another merchant's sale raises this too, so its existence stays hidden (404).
    """

    code: ClassVar[str] = "SALE_NOT_FOUND"


class IllegalSaleTransitionError(DomainError):
    """Raised when a command is not allowed in the sale's current status (SaleStateMachine).

    Examples: agreeing a plan twice, or issuing a new QR code once the customer has agreed.
    """

    code: ClassVar[str] = "SALE_STATE_CONFLICT"


class SessionCodesExhaustedError(DomainError):
    """Raised when every 4-digit session code is already shown on one of the shop's open sales."""

    code: ClassVar[str] = "SESSION_CODES_EXHAUSTED"


class ChosenPlanNoLongerOfferedError(DomainError):
    """Raised when the gateway no longer quotes the agreed plan exactly as the customer saw it.

    The payment link would otherwise carry different figures from the ones agreed to, so the
    hand-off is refused (409) and the customer has to choose again.
    """

    code: ClassVar[str] = "CHOSEN_PLAN_NO_LONGER_OFFERED"


class PaymentLinkAlreadyActiveError(DomainError):
    """Raised when a sale asks for a new payment link while its latest one may still be paid.

    The latest attempt is in progress, created, pending or has an unknown outcome, so a second
    link could let the customer pay twice. A known key still replays; a new link is allowed only
    once the latest attempt failed or was refused, or once the gateway reported an old
    outcome-unknown attempt NOT_FOUND.
    """

    code: ClassVar[str] = "PAYMENT_LINK_ALREADY_ACTIVE"


class InvalidReportingPeriodError(DomainError):
    """Raised when a report period cannot be used, such as a week that does not start on Monday.

    A week later than the current one is refused too: its message cannot be read or sent yet.
    """

    code: ClassVar[str] = "INVALID_REPORTING_PERIOD"


class InvalidReportDataError(DomainError):
    """Raised when a report figure, settlement batch or weekly message would be inconsistent."""

    code: ClassVar[str] = "INVALID_REPORT_DATA"


class InvalidComfortInputError(DomainError):
    """Raised when a comfort check cannot be worked out from its inputs.

    Examples: a monthly inflow of zero, an amount that is not Money, or comfort thresholds that are
    not whole basis points in increasing order.
    """

    code: ClassVar[str] = "INVALID_COMFORT_INPUT"
