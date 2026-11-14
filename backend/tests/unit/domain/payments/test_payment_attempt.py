"""Tests for the PaymentAttempt entity's invariants and its status values."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from emi_copilot.domain.errors import InvalidPaymentAttemptError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PaymentAttemptStatus
from tests.payment_builders import CREATED_AT, build_payment_attempt


def test_payment_attempt_with_valid_fields_keeps_them() -> None:
    """A valid attempt keeps its amount as Money and starts without gateway references."""
    payment_attempt = build_payment_attempt()
    assert payment_attempt.amount == Money.from_paise(2_200_000)
    assert payment_attempt.status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS
    assert payment_attempt.gateway_link_id is None


def test_payment_attempt_replace_with_gateway_references_returns_new_valid_attempt() -> None:
    """A status change produces a new instance and leaves the original untouched."""
    payment_attempt = build_payment_attempt()
    link_created_attempt = replace(
        payment_attempt,
        status=PaymentAttemptStatus.LINK_CREATED,
        gateway_link_id="link-sample-0001",
        payment_link_url="https://example.invalid/pay/link-sample-0001",
        updated_at=CREATED_AT + timedelta(seconds=2),
    )
    assert link_created_attempt.status is PaymentAttemptStatus.LINK_CREATED
    assert payment_attempt.status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS


def test_payment_attempt_is_immutable() -> None:
    """Fields cannot be reassigned; changes go through a new instance and the repository."""
    payment_attempt = build_payment_attempt()
    with pytest.raises(AttributeError):
        payment_attempt.status = PaymentAttemptStatus.PAID  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_overrides", "expected_message"),
    [
        ({"id": ""}, "payment attempt id"),
        ({"order_id": "  "}, "order id"),
        ({"idempotency_key": None}, "idempotency key"),
        ({"gateway_mode": ""}, "gateway mode"),
        ({"gateway_link_id": ""}, "gateway link id"),
        ({"payment_link_url": " "}, "payment link url"),
        ({"gateway_transaction_id": 42}, "gateway transaction id"),
        ({"request_fingerprint": "A" * 64}, "fingerprint"),
        ({"request_fingerprint": "a" * 63}, "fingerprint"),
        ({"request_fingerprint": None}, "fingerprint"),
        ({"amount": Money.from_paise(0)}, "above zero"),
        ({"amount": Money.from_rupees("1.005")}, "amount"),
        ({"amount": 2_200_000}, "amount"),
        ({"status": "PAID"}, "PaymentAttemptStatus"),
        ({"offer_snapshot": {"offer_id": "offer-plan-a"}}, "OfferSnapshot"),
        ({"created_at": datetime(2026, 11, 14, 10, 30)}, "created at"),  # noqa: DTZ001
        ({"updated_at": "2026-11-14T10:30:00Z"}, "updated at"),
        ({"updated_at": CREATED_AT - timedelta(microseconds=1)}, "before created at"),
    ],
)
def test_payment_attempt_with_invalid_field_raises_invalid_payment_attempt_error(
    field_overrides: dict[str, object], expected_message: str
) -> None:
    """Missing identifiers, a malformed fingerprint, bad money and bad timestamps are rejected."""
    with pytest.raises(InvalidPaymentAttemptError, match=expected_message):
        build_payment_attempt(**field_overrides)


def test_payment_attempt_status_values_are_stable_stored_words() -> None:
    """Statuses are stored by value, so each value equals its name and is part of the schema."""
    assert [status.value for status in PaymentAttemptStatus] == [
        "LINK_CREATION_IN_PROGRESS",
        "LINK_CREATED",
        "LINK_CREATION_FAILED",
        "OUTCOME_UNKNOWN",
        "PAYMENT_PENDING",
        "PAID",
        "PAYMENT_FAILED",
    ]
