"""Tests for the failure code stored when a create-link call certainly made no link."""

import pytest

from emi_copilot.domain.errors import (
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
    PaymentGatewayUnavailableError,
)
from emi_copilot.domain.payments import PaymentLinkFailureCode, find_payment_link_failure_code


def test_find_payment_link_failure_code_for_an_unsent_request_is_gateway_unavailable() -> None:
    """A request that never left is stored as GATEWAY_UNAVAILABLE (ADR 0010 section 3)."""
    error = PaymentGatewayUnavailableError("nothing was sent")
    assert find_payment_link_failure_code(error) is PaymentLinkFailureCode.GATEWAY_UNAVAILABLE


@pytest.mark.parametrize("rejection_reason", list(PaymentGatewayRejectionReason))
def test_find_payment_link_failure_code_for_a_refusal_is_its_reason(
    rejection_reason: PaymentGatewayRejectionReason,
) -> None:
    """Every refusal reason, GATEWAY_INTERNAL_ERROR included, has a code of the same name."""
    error = PaymentGatewayRequestRejectedError(rejection_reason, "refused")
    assert find_payment_link_failure_code(error).value == rejection_reason.value


def test_payment_link_failure_code_values_are_stable_stored_words() -> None:
    """Codes are stored by value, so each value equals its name and is part of the schema."""
    assert [code.value for code in PaymentLinkFailureCode] == [
        "GATEWAY_UNAVAILABLE",
        "INVALID_REQUEST",
        "DUPLICATE_ORDER_ID",
        "OPERATION_NOT_PERMITTED",
        "GATEWAY_INTERNAL_ERROR",
    ]
