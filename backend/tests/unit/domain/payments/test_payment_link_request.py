"""Tests for the PaymentLinkRequest value object."""

from dataclasses import fields

import pytest

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PaymentLinkRequest
from tests.payment_builders import build_payment_link_request, build_standard_offer_snapshot

CARD_FIELD_WORDS = ("card", "cvv", "expiry", "bin")


def test_payment_link_request_for_no_cost_plan_uses_the_price_as_amount() -> None:
    """On a no-cost plan the amount handed off is the price, which is also the total payable."""
    payment_link_request = build_payment_link_request()
    assert payment_link_request.amount == payment_link_request.offer.total_payable


def test_payment_link_request_for_standard_plan_uses_the_price_not_the_total_payable() -> None:
    """On a plan with extra cost the amount is the item price; the lender collects the extra."""
    payment_link_request = build_payment_link_request(offer=build_standard_offer_snapshot())
    assert payment_link_request.amount == Money.from_rupees("22000")


def test_payment_link_request_with_amount_other_than_plan_price_raises() -> None:
    """The amount must be the price the chosen plan was built on, so plan and charge agree."""
    with pytest.raises(InvalidPaymentGatewayValueError, match="price the chosen plan"):
        build_payment_link_request(amount=Money.from_rupees("23100"))


@pytest.mark.parametrize(
    ("field_overrides", "expected_message"),
    [
        ({"order_id": ""}, "order id"),
        ({"product_id": " "}, "product id"),
        ({"brand_id": None}, "brand id"),
        ({"category_id": ""}, "category id"),
        ({"customer_reference": ""}, "customer reference"),
        ({"amount": Money.from_paise(0)}, "amount"),
        ({"amount": Money.from_rupees("22000.001")}, "amount"),
        ({"offer": {"offer_id": "offer-plan-a"}}, "OfferSnapshot"),
    ],
)
def test_payment_link_request_with_invalid_field_raises_invalid_payment_gateway_value_error(
    field_overrides: dict[str, object], expected_message: str
) -> None:
    """Blank ids, a zero or sub-paise amount and an offer that is not a snapshot are rejected."""
    with pytest.raises(InvalidPaymentGatewayValueError, match=expected_message):
        build_payment_link_request(**field_overrides)


@pytest.mark.parametrize(
    "personal_customer_reference",
    ["customer@example.invalid", "9000000001", "+91 90000 00001", "(044) 2345-6789"],
)
def test_payment_link_request_with_email_or_phone_as_customer_reference_raises(
    personal_customer_reference: str,
) -> None:
    """An email address or phone number never leaves our system as the customer reference."""
    with pytest.raises(InvalidPaymentGatewayValueError, match="never an email or phone"):
        build_payment_link_request(customer_reference=personal_customer_reference)


@pytest.mark.parametrize("opaque_customer_reference", ["01JCSAMPLECUSTOMER00000001", "123456789"])
def test_payment_link_request_with_opaque_customer_reference_is_valid(
    opaque_customer_reference: str,
) -> None:
    """An opaque id, including a short number that cannot be a phone, is accepted."""
    payment_link_request = build_payment_link_request(customer_reference=opaque_customer_reference)
    assert payment_link_request.customer_reference == opaque_customer_reference


def test_payment_link_request_has_no_card_fields() -> None:
    """No card data is ever part of a payment link request (CLAUDE.md rule 3)."""
    for request_field in fields(PaymentLinkRequest):
        assert not any(card_word in request_field.name for card_word in CARD_FIELD_WORDS)


def test_payment_link_request_is_immutable() -> None:
    """A request cannot be changed after it is built."""
    payment_link_request = build_payment_link_request()
    with pytest.raises(AttributeError):
        payment_link_request.order_id = "ORDER-OTHER"  # type: ignore[misc]
