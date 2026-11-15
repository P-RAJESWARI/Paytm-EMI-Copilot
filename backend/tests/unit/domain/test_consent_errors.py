"""Typed errors of the customer session and consent flow (ADR 0022)."""

import pytest

from emi_copilot.domain.errors import (
    ConsentRecordChainConflictError,
    DomainError,
    InvalidConsentDataError,
    InvalidCustomerSessionDataError,
    OtpIncorrectError,
    OtpResendNotYetAvailableError,
    RetryLaterError,
)


def test_otp_incorrect_error_carries_the_attempts_left_and_keeps_its_code() -> None:
    """The screen can say "2 tries left" from the error, with the stable OTP_INCORRECT code."""
    error = OtpIncorrectError("This code does not match.", attempts_remaining=2)
    assert error.code == "OTP_INCORRECT"
    assert error.attempts_remaining == 2
    assert error.detail == "This code does not match."


@pytest.mark.parametrize("attempts_remaining", [0, -1, True])
def test_otp_incorrect_error_refuses_fewer_than_one_attempt_left(attempts_remaining: int) -> None:
    """The wrong code that uses the last attempt is OTP_EXPIRED, never OTP_INCORRECT with 0."""
    with pytest.raises(ValueError, match="at least one attempt"):
        OtpIncorrectError("This code does not match.", attempts_remaining=attempts_remaining)


def test_otp_resend_not_yet_available_error_is_a_retry_later_error_with_its_wait() -> None:
    """A resend asked for too soon answers 429 with Retry-After."""
    error = OtpResendNotYetAvailableError(12, "Wait before asking for a new code.")
    assert isinstance(error, RetryLaterError)
    assert error.retry_after_in_seconds == 12
    assert error.code == "OTP_RESEND_NOT_YET_AVAILABLE"


@pytest.mark.parametrize(
    ("error_class", "expected_code"),
    [
        (InvalidCustomerSessionDataError, "INVALID_CUSTOMER_SESSION_DATA"),
        (InvalidConsentDataError, "INVALID_CONSENT_DATA"),
        (ConsentRecordChainConflictError, "CONSENT_RECORD_CHAIN_CONFLICT"),
    ],
)
def test_consent_errors_are_domain_errors_with_stable_codes(
    error_class: type[DomainError], expected_code: str
) -> None:
    """Each error carries a stable code the frontend maps to calm, translated text."""
    error = error_class("detail for developers")
    assert isinstance(error, DomainError)
    assert error.code == expected_code
