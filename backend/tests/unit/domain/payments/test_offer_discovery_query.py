"""Tests for the OfferDiscoveryQuery value object."""

from dataclasses import replace

import pytest

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from tests.payment_builders import build_offer_discovery_query


def test_offer_discovery_query_with_valid_fields_keeps_them() -> None:
    """A complete query keeps the price and the opaque catalogue ids exactly as given."""
    offer_discovery_query = build_offer_discovery_query()
    assert offer_discovery_query.price == Money.from_paise(2_200_000)
    assert offer_discovery_query.product_id == "product-sample-0001"


@pytest.mark.parametrize(
    ("field_overrides", "expected_message"),
    [
        ({"price": Money.from_paise(0)}, "price"),
        ({"price": Money.from_rupees("22000.005")}, "price"),
        ({"price": 2_200_000}, "price"),
        ({"product_id": ""}, "product id"),
        ({"brand_id": "   "}, "brand id"),
        ({"category_id": None}, "category id"),
    ],
)
def test_offer_discovery_query_with_invalid_field_raises_invalid_payment_gateway_value_error(
    field_overrides: dict[str, object], expected_message: str
) -> None:
    """A zero, sub-paise or non-Money price and a blank id are rejected on creation."""
    with pytest.raises(InvalidPaymentGatewayValueError, match=expected_message):
        replace(build_offer_discovery_query(), **field_overrides)  # type: ignore[arg-type]


def test_offer_discovery_query_is_immutable() -> None:
    """A query cannot be changed after it is built."""
    offer_discovery_query = build_offer_discovery_query()
    with pytest.raises(AttributeError):
        offer_discovery_query.product_id = "other"  # type: ignore[misc]
