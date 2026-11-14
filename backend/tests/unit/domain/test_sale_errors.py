"""Tests for the sale errors and their stable codes."""

import pytest

from emi_copilot.domain.errors import (
    ChosenPlanNoLongerOfferedError,
    DomainError,
    IllegalSaleTransitionError,
    InvalidSaleDataError,
    PaymentLinkAlreadyActiveError,
    SaleNotFoundError,
    SessionCodesExhaustedError,
)


@pytest.mark.parametrize(
    ("error_class", "expected_code"),
    [
        (InvalidSaleDataError, "INVALID_SALE_DATA"),
        (SaleNotFoundError, "SALE_NOT_FOUND"),
        (IllegalSaleTransitionError, "SALE_STATE_CONFLICT"),
        (SessionCodesExhaustedError, "SESSION_CODES_EXHAUSTED"),
        (ChosenPlanNoLongerOfferedError, "CHOSEN_PLAN_NO_LONGER_OFFERED"),
        (PaymentLinkAlreadyActiveError, "PAYMENT_LINK_ALREADY_ACTIVE"),
    ],
)
def test_sale_errors_are_domain_errors_with_stable_codes(
    error_class: type[DomainError], expected_code: str
) -> None:
    """Each error carries the stable code the frontend translates."""
    error = error_class("detail for developers")
    assert isinstance(error, DomainError)
    assert error.code == expected_code
    assert error.detail == "detail for developers"
