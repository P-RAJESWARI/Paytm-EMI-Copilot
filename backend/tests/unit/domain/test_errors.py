"""Tests for the typed domain errors."""

import pytest

from emi_copilot.domain.errors import (
    DomainError,
    EmiScheduleNotRepresentableError,
    IdempotencyKeyReusedError,
    InvalidAuditEventError,
    InvalidEmiTermsError,
    InvalidMoneyAmountError,
    InvalidOfferSnapshotError,
    InvalidPaymentAttemptError,
    InvalidPaymentGatewayValueError,
    OfferNotFoundError,
    PaymentAttemptAlreadyExistsError,
    PaymentAttemptNotFoundError,
    PaymentGatewayError,
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
    PaymentGatewayTimeoutError,
    PaymentGatewayUnavailableError,
    PaymentLinkOutcomeUnknownError,
    WebhookSignatureInvalidError,
)
from emi_copilot.domain.money import Money


def test_invalid_money_amount_error_is_domain_error_with_stable_code() -> None:
    """The error carries a stable machine code and an English detail for problem+json."""
    with pytest.raises(InvalidMoneyAmountError) as raised_error:
        Money.from_rupees("abc")
    assert isinstance(raised_error.value, DomainError)
    assert raised_error.value.code == "INVALID_MONEY_AMOUNT"
    assert "abc" in raised_error.value.detail
    assert DomainError.code == "DOMAIN_ERROR"


@pytest.mark.parametrize(
    ("error_class", "expected_code"),
    [
        (InvalidEmiTermsError, "INVALID_EMI_TERMS"),
        (EmiScheduleNotRepresentableError, "EMI_SCHEDULE_NOT_REPRESENTABLE"),
        (InvalidOfferSnapshotError, "INVALID_OFFER_SNAPSHOT"),
        (InvalidPaymentAttemptError, "INVALID_PAYMENT_ATTEMPT"),
        (InvalidAuditEventError, "INVALID_AUDIT_EVENT"),
        (PaymentAttemptAlreadyExistsError, "PAYMENT_ATTEMPT_ALREADY_EXISTS"),
        (PaymentAttemptNotFoundError, "PAYMENT_ATTEMPT_NOT_FOUND"),
        (InvalidPaymentGatewayValueError, "INVALID_PAYMENT_GATEWAY_VALUE"),
        (PaymentGatewayError, "PAYMENT_GATEWAY_ERROR"),
        (PaymentGatewayTimeoutError, "PAYMENT_GATEWAY_TIMEOUT"),
        (PaymentGatewayUnavailableError, "PAYMENT_GATEWAY_UNAVAILABLE"),
        (WebhookSignatureInvalidError, "WEBHOOK_SIGNATURE_INVALID"),
        (OfferNotFoundError, "OFFER_NOT_FOUND"),
        (IdempotencyKeyReusedError, "IDEMPOTENCY_KEY_REUSED"),
        (PaymentLinkOutcomeUnknownError, "PAYMENT_LINK_OUTCOME_UNKNOWN"),
    ],
)
def test_domain_errors_are_domain_errors_with_stable_codes(
    error_class: type[DomainError], expected_code: str
) -> None:
    """Each typed error carries a stable machine code so the API can map it to problem+json."""
    error = error_class("detail for developers")
    assert isinstance(error, DomainError)
    assert error.code == expected_code
    assert error.detail == "detail for developers"


@pytest.mark.parametrize(
    "gateway_error_class", [PaymentGatewayTimeoutError, PaymentGatewayUnavailableError]
)
def test_gateway_call_failures_share_the_payment_gateway_error_base(
    gateway_error_class: type[PaymentGatewayError],
) -> None:
    """Services can handle every failed gateway call through one base class."""
    assert issubclass(gateway_error_class, PaymentGatewayError)


@pytest.mark.parametrize(
    "caller_error_class",
    [
        WebhookSignatureInvalidError,
        OfferNotFoundError,
        IdempotencyKeyReusedError,
        PaymentLinkOutcomeUnknownError,
        InvalidPaymentGatewayValueError,
    ],
)
def test_errors_about_the_request_are_not_gateway_call_failures(
    caller_error_class: type[DomainError],
) -> None:
    """A bad signature, offer, key or value is not mistaken for a failed gateway call."""
    assert not issubclass(caller_error_class, PaymentGatewayError)


def test_payment_gateway_request_rejected_error_carries_a_stable_domain_reason() -> None:
    """A rejection says why in our own words and keeps no vendor payload."""
    rejected_error = PaymentGatewayRequestRejectedError(
        PaymentGatewayRejectionReason.DUPLICATE_ORDER_ID, "The order id already has a link."
    )
    assert isinstance(rejected_error, PaymentGatewayError)
    assert rejected_error.code == "PAYMENT_GATEWAY_REQUEST_REJECTED"
    assert rejected_error.reason is PaymentGatewayRejectionReason.DUPLICATE_ORDER_ID
    assert rejected_error.detail == "The order id already has a link."


def test_payment_gateway_rejection_reason_values_are_stable_words() -> None:
    """Rejection reasons may reach problem+json bodies and audit details, so values are stable."""
    assert [reason.value for reason in PaymentGatewayRejectionReason] == [
        "INVALID_REQUEST",
        "DUPLICATE_ORDER_ID",
        "OPERATION_NOT_PERMITTED",
    ]
