"""Tests for GatewayPaymentStatus and the PaymentStatusResult value object."""

import pytest

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import GatewayPaymentStatus, PaymentStatusResult

AMOUNT_PAID = Money.from_rupees("22000")
TRANSACTION_ID = "transaction-sample-0001"


@pytest.mark.parametrize(
    ("status", "gateway_transaction_id", "amount_paid"),
    [
        (GatewayPaymentStatus.PAID, TRANSACTION_ID, AMOUNT_PAID),
        (GatewayPaymentStatus.PENDING, TRANSACTION_ID, None),
        (GatewayPaymentStatus.PENDING, None, None),
        (GatewayPaymentStatus.FAILED, TRANSACTION_ID, None),
        (GatewayPaymentStatus.FAILED, None, None),
        (GatewayPaymentStatus.NOT_FOUND, None, None),
    ],
)
def test_payment_status_result_with_consistent_outcome_is_valid(
    status: GatewayPaymentStatus, gateway_transaction_id: str | None, amount_paid: Money | None
) -> None:
    """Each status accepts exactly the transaction id and amount that fit it."""
    payment_status_result = PaymentStatusResult(
        "ORDER-SAMPLE-0001", status, gateway_transaction_id, amount_paid
    )
    assert payment_status_result.status is status


@pytest.mark.parametrize(
    ("order_id", "status", "gateway_transaction_id", "amount_paid", "expected_message"),
    [
        ("", GatewayPaymentStatus.PENDING, None, None, "order id"),
        ("ORDER-SAMPLE-0001", "PAID", TRANSACTION_ID, AMOUNT_PAID, "GatewayPaymentStatus"),
        ("ORDER-SAMPLE-0001", GatewayPaymentStatus.PENDING, " ", None, "gateway transaction id"),
        ("ORDER-SAMPLE-0001", GatewayPaymentStatus.PAID, None, AMOUNT_PAID, "paid outcome needs"),
        ("ORDER-SAMPLE-0001", GatewayPaymentStatus.PAID, TRANSACTION_ID, None, "paid outcome"),
        (
            "ORDER-SAMPLE-0001",
            GatewayPaymentStatus.PAID,
            TRANSACTION_ID,
            Money.from_paise(0),
            "amount paid",
        ),
        (
            "ORDER-SAMPLE-0001",
            GatewayPaymentStatus.FAILED,
            TRANSACTION_ID,
            AMOUNT_PAID,
            "Only a paid outcome",
        ),
        (
            "ORDER-SAMPLE-0001",
            GatewayPaymentStatus.NOT_FOUND,
            TRANSACTION_ID,
            None,
            "unknown order",
        ),
    ],
)
def test_payment_status_result_with_inconsistent_outcome_raises_invalid_value_error(
    order_id: str,
    status: object,
    gateway_transaction_id: str | None,
    amount_paid: Money | None,
    expected_message: str,
) -> None:
    """A transaction id or amount that does not fit the status is rejected on creation."""
    with pytest.raises(InvalidPaymentGatewayValueError, match=expected_message):
        PaymentStatusResult(order_id, status, gateway_transaction_id, amount_paid)  # type: ignore[arg-type]


def test_gateway_payment_status_values_are_our_own_stable_words() -> None:
    """Statuses are our words, so adapters map every vendor status onto exactly these four."""
    assert [status.value for status in GatewayPaymentStatus] == [
        "PAID",
        "PENDING",
        "FAILED",
        "NOT_FOUND",
    ]


def test_payment_status_result_is_immutable() -> None:
    """A status answer cannot be changed after it is received."""
    payment_status_result = PaymentStatusResult(
        "ORDER-SAMPLE-0001", GatewayPaymentStatus.NOT_FOUND, None, None
    )
    with pytest.raises(AttributeError):
        payment_status_result.status = GatewayPaymentStatus.PAID  # type: ignore[misc]
