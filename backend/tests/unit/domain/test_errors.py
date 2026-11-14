"""Tests for the typed domain errors."""

import pytest

from emi_copilot.domain.errors import DomainError, InvalidMoneyAmountError
from emi_copilot.domain.money import Money


def test_invalid_money_amount_error_is_domain_error_with_stable_code() -> None:
    """The error carries a stable machine code and an English detail for problem+json."""
    with pytest.raises(InvalidMoneyAmountError) as raised_error:
        Money.from_rupees("abc")
    assert isinstance(raised_error.value, DomainError)
    assert raised_error.value.code == "INVALID_MONEY_AMOUNT"
    assert "abc" in raised_error.value.detail
    assert DomainError.code == "DOMAIN_ERROR"
