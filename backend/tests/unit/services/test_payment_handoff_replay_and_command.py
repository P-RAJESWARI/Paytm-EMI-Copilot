"""Tests for the create-link command, its fingerprint, and replaying a stored attempt."""

import hashlib

import pytest

from emi_copilot.domain.errors import (
    InvalidPaymentAttemptError,
    InvalidPaymentGatewayValueError,
    PaymentLinkOutcomeUnknownError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PaymentAttemptStatus
from emi_copilot.services.create_link_outcome import replay_stored_outcome
from emi_copilot.services.payment_handoff_types import CreatePaymentLinkCommand
from tests.payment_builders import SAMPLE_REQUEST_FINGERPRINT, build_payment_attempt

SAMPLE_PAYMENT_URL = "https://fake-gateway.invalid/pay/sample"


def _build_command(
    idempotency_key: str = "key-0001", **overrides: object
) -> CreatePaymentLinkCommand:
    """Builds a command for plan A on the sample item, with overridable fields."""
    fields: dict[str, object] = {
        "offer_id": "offer-plan-a",
        "price": Money.from_rupees("22000"),
        "product_id": "product-sample-0001",
        "brand_id": "brand-sample-0001",
        "category_id": "category-sample-0001",
    }
    return CreatePaymentLinkCommand(idempotency_key, **(fields | overrides))  # type: ignore[arg-type]


def test_calculate_request_fingerprint_is_sha256_of_the_sorted_compact_body() -> None:
    """The fingerprint is reproducible by hand and leaves the idempotency key out."""
    expected_canonical_text = (
        '{"brand_id":"brand-sample-0001","category_id":"category-sample-0001",'
        '"offer_id":"offer-plan-a","price_in_paise":2200000,"product_id":"product-sample-0001"}'
    )
    expected_fingerprint = hashlib.sha256(expected_canonical_text.encode("utf-8")).hexdigest()
    assert _build_command().calculate_request_fingerprint() == expected_fingerprint
    assert _build_command("key-0002").calculate_request_fingerprint() == expected_fingerprint


@pytest.mark.parametrize("unusable_key", ["", "   ", "k" * 256])
def test_create_payment_link_command_with_an_unusable_key_raises(unusable_key: str) -> None:
    """The key must be 1 to 255 characters, the size of its column."""
    with pytest.raises(InvalidPaymentAttemptError, match="idempotency key"):
        _build_command(unusable_key)


def test_create_payment_link_command_with_an_unusable_item_raises() -> None:
    """A blank item id or a sub-paise price could never be quoted, so it fails at once."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        _build_command(product_id=" ")
    with pytest.raises(InvalidPaymentGatewayValueError):
        _build_command(price=Money.from_rupees("1.005"))


@pytest.mark.parametrize(
    "later_status",
    [PaymentAttemptStatus.PAYMENT_PENDING, PaymentAttemptStatus.PAID],
)
def test_replay_stored_outcome_of_a_paid_or_pending_link_returns_the_link(
    later_status: PaymentAttemptStatus,
) -> None:
    """A link the customer has since used is still the stored result of its key."""
    stored_attempt = build_payment_attempt(
        status=later_status, gateway_link_id="link-sample", payment_link_url=SAMPLE_PAYMENT_URL
    )
    handoff = replay_stored_outcome(stored_attempt, SAMPLE_REQUEST_FINGERPRINT)
    assert (handoff.payment_url, handoff.status, handoff.is_replay) == (
        SAMPLE_PAYMENT_URL,
        later_status,
        True,
    )


def test_replay_stored_outcome_moved_on_from_unknown_without_a_link_raises_unknown() -> None:
    """A status report found the payment, but we never learned the link: still unknown here."""
    stored_attempt = build_payment_attempt(status=PaymentAttemptStatus.PAYMENT_PENDING)
    with pytest.raises(PaymentLinkOutcomeUnknownError):
        replay_stored_outcome(stored_attempt, SAMPLE_REQUEST_FINGERPRINT)
