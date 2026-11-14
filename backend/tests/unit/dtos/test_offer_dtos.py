"""Offer DTOs speak camelCase, keep money in bounded integer paise and refuse unknown fields."""

import pytest
from pydantic import ValidationError

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiOffer, EmiType, price_emi_offer
from emi_copilot.dtos.offer_dtos import EmiOfferResponse, OffersQuery
from emi_copilot.dtos.wire_types import MAXIMUM_SAFE_JAVASCRIPT_INTEGER

VALID_QUERY = {"priceInPaise": "2200000", "productId": "p", "brandId": "b", "categoryId": "c"}


def test_maximum_safe_javascript_integer_is_two_to_the_53_minus_one() -> None:
    """The cap is Number.MAX_SAFE_INTEGER, the largest integer a browser parses exactly."""
    assert MAXIMUM_SAFE_JAVASCRIPT_INTEGER == 2**53 - 1


def test_offers_query_reads_camel_case_and_parses_paise_from_query_text() -> None:
    """Query values arrive as text, so the price is parsed from its digits into Money."""
    discovery_query = OffersQuery.model_validate(VALID_QUERY).to_offer_discovery_query()
    assert discovery_query.price == Money.from_paise(2_200_000)
    assert (discovery_query.product_id, discovery_query.brand_id) == ("p", "b")


@pytest.mark.parametrize(
    "price_in_paise", ["0", "-1", str(MAXIMUM_SAFE_JAVASCRIPT_INTEGER + 1), "12.5", "abc"]
)
def test_offers_query_refuses_prices_outside_positive_safe_integers(price_in_paise: str) -> None:
    """Zero, negative, unsafe-sized and fractional prices never reach the gateway."""
    with pytest.raises(ValidationError):
        OffersQuery.model_validate({**VALID_QUERY, "priceInPaise": price_in_paise})


def test_offers_query_accepts_the_largest_safe_price() -> None:
    """Exactly Number.MAX_SAFE_INTEGER paise is still valid on the wire."""
    offers_query = OffersQuery.model_validate(
        {**VALID_QUERY, "priceInPaise": str(MAXIMUM_SAFE_JAVASCRIPT_INTEGER)}
    )
    assert offers_query.price_in_paise == MAXIMUM_SAFE_JAVASCRIPT_INTEGER


def test_offers_query_refuses_unknown_parameters() -> None:
    """Unknown parameters, card fields included, are never silently accepted."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        OffersQuery.model_validate({**VALID_QUERY, "cardNumber": "4111"})


def test_emi_offer_response_serialises_camel_case_paise() -> None:
    """Responses are dumped by alias, with the lender's monthly figure and our exact totals."""
    offer = EmiOffer(
        offer_id="offer-plan-a",
        lender_label="Brand",
        emi_type=EmiType.NO_COST,
        tenure_in_months=6,
        quoted_monthly_installment=Money.from_rupees("3666.67"),
        quoted_extra_in_total=Money.from_paise(0),
    )
    response = EmiOfferResponse.from_priced_offer(
        price_emi_offer(offer, Money.from_rupees("22000"))
    )
    assert response.model_dump(mode="json", by_alias=True) == {
        "offerId": "offer-plan-a",
        "lenderLabel": "Brand",
        "emiType": "NO_COST",
        "tenureInMonths": 6,
        "monthlyInstallmentInPaise": 366_667,
        "lastInstallmentInPaise": 366_665,
        "extraInTotalInPaise": 0,
        "totalPayableInPaise": 2_200_000,
        "priceInPaise": 2_200_000,
    }
