"""Tests for the typed domain errors."""

import pytest

from emi_copilot.domain.errors import (
    DomainError,
    EmiScheduleNotRepresentableError,
    InvalidAuditEventError,
    InvalidEmiTermsError,
    InvalidMoneyAmountError,
    InvalidOfferSnapshotError,
    InvalidPaymentAttemptError,
    PaymentAttemptAlreadyExistsError,
    PaymentAttemptNotFoundError,
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
