"""Tests for the PaymentLink value object."""

import pytest

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.payments import PaymentLink

SAMPLE_PAYMENT_URL = "https://payments.example.invalid/pay/link-sample-0001"


def test_payment_link_with_https_url_keeps_its_fields() -> None:
    """A link with an absolute https URL keeps the order id, link id and URL as given."""
    payment_link = PaymentLink("ORDER-SAMPLE-0001", "link-sample-0001", SAMPLE_PAYMENT_URL)
    assert payment_link.payment_url == SAMPLE_PAYMENT_URL


@pytest.mark.parametrize(
    ("order_id", "gateway_link_id", "payment_url", "expected_message"),
    [
        ("", "link-sample-0001", SAMPLE_PAYMENT_URL, "order id"),
        ("ORDER-SAMPLE-0001", " ", SAMPLE_PAYMENT_URL, "gateway link id"),
        ("ORDER-SAMPLE-0001", "link-sample-0001", "", "payment url"),
        ("ORDER-SAMPLE-0001", "link-sample-0001", "http://payments.example.invalid/pay", "https"),
        ("ORDER-SAMPLE-0001", "link-sample-0001", "/pay/link-sample-0001", "https"),
        ("ORDER-SAMPLE-0001", "link-sample-0001", "https:///pay/link-sample-0001", "https"),
    ],
)
def test_payment_link_with_invalid_field_raises_invalid_payment_gateway_value_error(
    order_id: str, gateway_link_id: str, payment_url: str, expected_message: str
) -> None:
    """Blank ids and any URL that is not absolute https with a host are rejected."""
    with pytest.raises(InvalidPaymentGatewayValueError, match=expected_message):
        PaymentLink(order_id, gateway_link_id, payment_url)


def test_payment_link_is_immutable() -> None:
    """A link cannot be changed after the gateway made it."""
    payment_link = PaymentLink("ORDER-SAMPLE-0001", "link-sample-0001", SAMPLE_PAYMENT_URL)
    with pytest.raises(AttributeError):
        payment_link.payment_url = "https://elsewhere.example.invalid"  # type: ignore[misc]
