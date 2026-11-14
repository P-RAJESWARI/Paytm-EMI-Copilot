"""Tests for the merchant pairing, authentication and catalogue errors."""

import pytest

from emi_copilot.domain.errors import (
    DomainError,
    InvalidMerchantDataError,
    InvalidPairingCredentialsError,
    MerchantAuthenticationRequiredError,
    PairingTemporarilyLockedError,
    ProductNotFoundError,
    RequestRateLimitedError,
    RetryLaterError,
)


@pytest.mark.parametrize(
    ("error_class", "expected_code"),
    [
        (InvalidMerchantDataError, "INVALID_MERCHANT_DATA"),
        (InvalidPairingCredentialsError, "INVALID_PAIRING_CREDENTIALS"),
        (MerchantAuthenticationRequiredError, "MERCHANT_AUTHENTICATION_REQUIRED"),
        (ProductNotFoundError, "PRODUCT_NOT_FOUND"),
    ],
)
def test_merchant_errors_are_domain_errors_with_stable_codes(
    error_class: type[DomainError], expected_code: str
) -> None:
    """Each error carries the stable code the frontend translates."""
    error = error_class("detail for developers")
    assert isinstance(error, DomainError)
    assert error.code == expected_code
    assert error.detail == "detail for developers"


@pytest.mark.parametrize(
    ("error_class", "expected_code"),
    [
        (PairingTemporarilyLockedError, "PAIRING_TEMPORARILY_LOCKED"),
        (RequestRateLimitedError, "RATE_LIMITED"),
        (RetryLaterError, "RETRY_LATER"),
    ],
)
def test_retry_later_errors_carry_the_seconds_to_wait(
    error_class: type[RetryLaterError], expected_code: str
) -> None:
    """A refusal that ends by itself tells the caller how long to wait (Retry-After)."""
    error = error_class(42, "Wait a little.")
    assert isinstance(error, RetryLaterError)
    assert error.code == expected_code
    assert error.retry_after_in_seconds == 42
    assert error.detail == "Wait a little."


@pytest.mark.parametrize("unusable_delay", [0, -1, True])
def test_retry_later_error_with_delay_below_one_second_raises(unusable_delay: int) -> None:
    """Retry-After is a whole number of seconds, at least one."""
    with pytest.raises(ValueError, match="at least one"):
        PairingTemporarilyLockedError(unusable_delay, "Locked.")
