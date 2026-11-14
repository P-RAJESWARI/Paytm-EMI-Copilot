"""The Mock gateway's signed webhook format: HMAC-SHA256 over sorted fields, checked first."""

import hmac
from collections.abc import Callable

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.mock_webhook_signature import (
    build_canonical_signed_text,
    calculate_mock_webhook_signature,
)
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError, WebhookSignatureInvalidError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    GatewayPaymentStatus,
    UnverifiedWebhookNotification,
    VerifiedWebhookEvent,
)
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT

SYNTHETIC_WEBHOOK_SIGNING_SECRET = bytes(range(32))
OTHER_SYNTHETIC_WEBHOOK_SIGNING_SECRET = bytes(range(1, 33))
SAMPLE_SIGNED_FIELDS = {
    "orderId": "ORDER-SAMPLE-0001",
    "status": "PAID",
    "transactionId": "transaction-sample-0001",
    "amountInPaise": "2200000",
}
# Known answer, computed once with Python's hmac module and the synthetic secret above.
SAMPLE_SIGNATURE = (
    "eedbbf6f91f27ee5ff9a13fbaf792cb79feaef9fec859a5e8913b0bacf030771"  # pragma: allowlist secret
)


@pytest.fixture
def mock_gateway() -> MockPaymentGatewayAdapter:
    """Gives a fresh Mock that signs and verifies with the synthetic secret."""
    return MockPaymentGatewayAdapter(FixedClock(CREATED_AT), SYNTHETIC_WEBHOOK_SIGNING_SECRET)


def sign_fields(signed_fields: dict[str, str]) -> UnverifiedWebhookNotification:
    """Builds a notification whose signature genuinely covers the given fields."""
    signature = calculate_mock_webhook_signature(signed_fields, SYNTHETIC_WEBHOOK_SIGNING_SECRET)
    return UnverifiedWebhookNotification(received_fields={**signed_fields, "signature": signature})


def test_build_canonical_signed_text_is_compact_json_with_keys_sorted() -> None:
    """The signed text does not depend on the order in which fields arrived."""
    reversed_fields = dict(reversed(list(SAMPLE_SIGNED_FIELDS.items())))
    assert build_canonical_signed_text(reversed_fields) == (
        '{"amountInPaise":"2200000","orderId":"ORDER-SAMPLE-0001",'
        '"status":"PAID","transactionId":"transaction-sample-0001"}'
    )


def test_calculate_mock_webhook_signature_matches_the_known_answer() -> None:
    """The signature is the hex HMAC-SHA256 of the canonical text under the secret."""
    signature = calculate_mock_webhook_signature(
        SAMPLE_SIGNED_FIELDS, SYNTHETIC_WEBHOOK_SIGNING_SECRET
    )
    assert signature == SAMPLE_SIGNATURE


def test_build_signed_notification_signs_every_field_with_the_known_answer(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """The Mock's helper produces exactly the documented fields and signature."""
    notification = mock_gateway.build_signed_notification(
        "ORDER-SAMPLE-0001",
        GatewayPaymentStatus.PAID,
        "transaction-sample-0001",
        Money.from_rupees("22000"),
    )
    assert dict(notification.received_fields) == {
        **SAMPLE_SIGNED_FIELDS,
        "signature": SAMPLE_SIGNATURE,
    }


def test_verify_webhook_reads_a_genuine_notification_in_any_field_order(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """Fields received in a different order still verify, because signing sorts them."""
    reordered_fields = {
        "signature": SAMPLE_SIGNATURE,
        **dict(reversed(SAMPLE_SIGNED_FIELDS.items())),
    }
    verified_event = mock_gateway.verify_webhook(
        UnverifiedWebhookNotification(received_fields=reordered_fields)
    )
    assert verified_event == VerifiedWebhookEvent(
        order_id="ORDER-SAMPLE-0001",
        status=GatewayPaymentStatus.PAID,
        gateway_transaction_id="transaction-sample-0001",
        amount_paid=Money.from_rupees("22000"),
    )


def test_verify_webhook_reads_empty_transaction_and_amount_as_absent(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """A pending update without a transaction or an amount round-trips through the helper."""
    notification = mock_gateway.build_signed_notification(
        "ORDER-SAMPLE-0001", GatewayPaymentStatus.PENDING, None, None
    )
    assert mock_gateway.verify_webhook(notification) == VerifiedWebhookEvent(
        order_id="ORDER-SAMPLE-0001",
        status=GatewayPaymentStatus.PENDING,
        gateway_transaction_id=None,
        amount_paid=None,
    )


def remove_field(field_name: str) -> Callable[[dict[str, str]], None]:
    """Gives a change that deletes one received field."""

    def delete_field(received_fields: dict[str, str]) -> None:
        """Deletes the field from the received fields."""
        del received_fields[field_name]

    return delete_field


def set_field(field_name: str, value: str) -> Callable[[dict[str, str]], None]:
    """Gives a change that sets one received field to a value."""

    def overwrite_field(received_fields: dict[str, str]) -> None:
        """Sets the field to the value, adding it when it was not received."""
        received_fields[field_name] = value

    return overwrite_field


@pytest.mark.parametrize(
    "change_received_fields",
    [
        remove_field("signature"),
        remove_field("transactionId"),
        set_field("note", "added after signing"),
        set_field("amountInPaise", "2200001"),
        set_field("orderId", "ORDER-SAMPLE-0002"),
        set_field("status", "FAILED"),
        set_field("signature", "0" * 64),
        set_field("signature", SAMPLE_SIGNATURE.upper()),
        set_field("signature", "not hex at all, ü"),
    ],
    ids=[
        "signature-missing",
        "signed-field-missing",
        "extra-field",
        "amount-tampered",
        "order-id-tampered",
        "status-tampered",
        "wrong-signature",
        "signature-case-changed",
        "signature-not-hex",
    ],
)
def test_verify_webhook_with_missing_extra_or_tampered_fields_raises_signature_invalid(
    mock_gateway: MockPaymentGatewayAdapter,
    change_received_fields: Callable[[dict[str, str]], None],
) -> None:
    """Any field missing, added or changed after signing fails the signature check."""
    received_fields = {**SAMPLE_SIGNED_FIELDS, "signature": SAMPLE_SIGNATURE}
    change_received_fields(received_fields)
    with pytest.raises(WebhookSignatureInvalidError):
        mock_gateway.verify_webhook(UnverifiedWebhookNotification(received_fields=received_fields))


def test_verify_webhook_signed_with_another_secret_raises_signature_invalid(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """Only the holder of this adapter's secret can produce a notification it accepts."""
    forged_signature = calculate_mock_webhook_signature(
        SAMPLE_SIGNED_FIELDS, OTHER_SYNTHETIC_WEBHOOK_SIGNING_SECRET
    )
    forged_notification = UnverifiedWebhookNotification(
        received_fields={**SAMPLE_SIGNED_FIELDS, "signature": forged_signature}
    )
    with pytest.raises(WebhookSignatureInvalidError):
        mock_gateway.verify_webhook(forged_notification)


def test_verify_webhook_checks_the_signature_before_reading_any_malformed_field(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """An unsigned body with garbage values is a signature failure, never a parsing error."""
    garbage_notification = UnverifiedWebhookNotification(
        received_fields={
            "orderId": "",
            "status": "NOT-A-STATUS",
            "transactionId": "",
            "amountInPaise": "lots",
            "signature": "0" * 64,
        }
    )
    with pytest.raises(WebhookSignatureInvalidError):
        mock_gateway.verify_webhook(garbage_notification)


def test_verify_webhook_compares_signatures_in_constant_time(
    mock_gateway: MockPaymentGatewayAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The signature is compared with hmac.compare_digest, so timing reveals nothing."""
    compared_values: list[tuple[bytes, bytes]] = []
    real_compare_digest = hmac.compare_digest

    def record_compare_digest(first_value: bytes, second_value: bytes) -> bool:
        """Records the compared values, then defers to the real constant-time comparison."""
        compared_values.append((first_value, second_value))
        return real_compare_digest(first_value, second_value)

    monkeypatch.setattr(hmac, "compare_digest", record_compare_digest)
    mock_gateway.verify_webhook(sign_fields(SAMPLE_SIGNED_FIELDS))
    assert compared_values == [(SAMPLE_SIGNATURE.encode(), SAMPLE_SIGNATURE.encode())]


@pytest.mark.parametrize(
    ("field_name", "malformed_value"),
    [
        ("status", "SETTLED"),
        ("status", "NOT_FOUND"),
        ("orderId", ""),
        ("amountInPaise", "22000.00"),
        ("amountInPaise", "-1"),
        ("amountInPaise", "0"),
        ("amountInPaise", "9" * 19),
        ("amountInPaise", "9" * 20),
        ("amountInPaise", ""),
    ],
    ids=[
        "unknown-status",
        "not-found-status",
        "blank-order-id",
        "amount-in-rupees",
        "negative-amount",
        "zero-amount",
        "amount-above-money-limit",
        "amount-too-many-digits",
        "paid-without-amount",
    ],
)
def test_verify_webhook_genuinely_signed_but_malformed_raises_invalid_value(
    mock_gateway: MockPaymentGatewayAdapter, field_name: str, malformed_value: str
) -> None:
    """A genuine sender with a malformed body is a bad gateway value, not a forged webhook."""
    malformed_notification = sign_fields({**SAMPLE_SIGNED_FIELDS, field_name: malformed_value})
    with pytest.raises(InvalidPaymentGatewayValueError):
        mock_gateway.verify_webhook(malformed_notification)
