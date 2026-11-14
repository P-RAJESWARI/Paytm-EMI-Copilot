"""Tests for the untrusted webhook notification and the verified webhook event."""

import pytest

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    GatewayPaymentStatus,
    UnverifiedWebhookNotification,
    VerifiedWebhookEvent,
)

SAMPLE_RECEIVED_FIELDS = {"ORDER": "ORDER-SAMPLE-0001", "SIGNATURE": "signature-sample-value"}


def test_unverified_webhook_notification_keeps_a_copy_of_the_received_fields() -> None:
    """Changing the caller's dictionary afterwards does not change the received notification."""
    received_fields = dict(SAMPLE_RECEIVED_FIELDS)
    notification = UnverifiedWebhookNotification(received_fields)
    received_fields["ORDER"] = "ORDER-TAMPERED"
    assert notification.received_fields == SAMPLE_RECEIVED_FIELDS


def test_unverified_webhook_notification_fields_are_read_only() -> None:
    """No code can change a received field before or after signature verification."""
    notification = UnverifiedWebhookNotification(dict(SAMPLE_RECEIVED_FIELDS))
    with pytest.raises(TypeError):
        notification.received_fields["ORDER"] = "ORDER-TAMPERED"  # type: ignore[index]
    with pytest.raises(AttributeError):
        notification.received_fields = {}  # type: ignore[misc]


def test_unverified_webhook_notification_repr_shows_field_names_but_no_values() -> None:
    """The repr never exposes the signature or any other untrusted value, so it is safe to log."""
    notification_text = repr(UnverifiedWebhookNotification(dict(SAMPLE_RECEIVED_FIELDS)))
    assert notification_text == "UnverifiedWebhookNotification(field_names=['ORDER', 'SIGNATURE'])"


def test_unverified_webhook_notification_with_no_fields_is_accepted_for_verification() -> None:
    """An empty notification is still received; signature verification is what rejects it."""
    assert UnverifiedWebhookNotification({}).received_fields == {}


@pytest.mark.parametrize(
    "received_fields",
    [[("ORDER", "ORDER-SAMPLE-0001")], {"ORDER": 7}, {7: "ORDER-SAMPLE-0001"}],
)
def test_unverified_webhook_notification_with_non_text_fields_raises_invalid_value_error(
    received_fields: object,
) -> None:
    """Received fields must be a mapping of text to text, exactly as a form post gives them."""
    with pytest.raises(InvalidPaymentGatewayValueError, match="text"):
        UnverifiedWebhookNotification(received_fields)  # type: ignore[arg-type]


def test_verified_webhook_event_for_paid_payment_keeps_its_fields() -> None:
    """A verified paid event carries the order id, transaction id and amount paid."""
    verified_event = VerifiedWebhookEvent(
        "ORDER-SAMPLE-0001",
        GatewayPaymentStatus.PAID,
        "transaction-sample-0001",
        Money.from_rupees("22000"),
    )
    assert verified_event.amount_paid == Money.from_paise(2_200_000)


@pytest.mark.parametrize(
    ("order_id", "status", "gateway_transaction_id", "expected_message"),
    [
        ("", GatewayPaymentStatus.FAILED, None, "order id"),
        ("ORDER-SAMPLE-0001", GatewayPaymentStatus.NOT_FOUND, None, "cannot report NOT_FOUND"),
        ("ORDER-SAMPLE-0001", GatewayPaymentStatus.PAID, None, "paid outcome needs"),
    ],
)
def test_verified_webhook_event_with_inconsistent_fields_raises_invalid_value_error(
    order_id: str,
    status: GatewayPaymentStatus,
    gateway_transaction_id: str | None,
    expected_message: str,
) -> None:
    """A blank order id, a NOT_FOUND status or an outcome that does not fit is rejected."""
    with pytest.raises(InvalidPaymentGatewayValueError, match=expected_message):
        VerifiedWebhookEvent(order_id, status, gateway_transaction_id, None)
