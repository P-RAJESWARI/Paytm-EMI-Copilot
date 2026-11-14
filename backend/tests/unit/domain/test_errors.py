"""Tests for the typed domain errors."""

import pytest

from emi_copilot.domain.errors import (
    DomainError,
    EmiScheduleNotRepresentableError,
    InvalidEmiTermsError,
    InvalidMoneyAmountError,
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
    ],
)
def test_emi_errors_are_domain_errors_with_stable_codes(
    error_class: type[DomainError], expected_code: str
) -> None:
    """EMI errors carry stable machine codes so the API can map them to problem+json."""
    error = error_class("detail for developers")
    assert isinstance(error, DomainError)
    assert error.code == expected_code
    assert error.detail == "detail for developers"
