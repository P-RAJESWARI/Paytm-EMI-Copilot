"""Tests for catalogue products and the summary of the EMI offers on each."""

import pytest

from emi_copilot.domain.catalogue import (
    CatalogueProduct,
    ProductOfferSummary,
    summarise_priced_offers,
)
from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    EmiOffer,
    EmiType,
    OfferDiscoveryQuery,
    price_emi_offer,
)

SAMPLE_PRICE = Money.from_rupees("22000")


def build_product(**overrides: object) -> CatalogueProduct:
    """A synthetic ₹22,000 product with synthetic gateway ids."""
    fields: dict[str, object] = {
        "id": "01JCPRODUCT000000000000001",
        "merchant_id": "01JCMERCHANT00000000000001",
        "name": "Example phone, 128 GB",
        "list_price": SAMPLE_PRICE,
        "gateway_product_id": "product-synthetic-1",
        "gateway_brand_id": "brand-synthetic",
        "gateway_category_id": "category-synthetic",
    }
    fields.update(overrides)
    return CatalogueProduct(**fields)  # type: ignore[arg-type]


def build_offer(offer_id: str, emi_type: EmiType, monthly: str, extra: str) -> EmiOffer:
    """A six-month offer quoted with the given monthly figure and extra, in rupees."""
    return EmiOffer(
        offer_id=offer_id,
        lender_label="Synthetic lender",
        emi_type=emi_type,
        tenure_in_months=6,
        quoted_monthly_installment=Money.from_rupees(monthly),
        quoted_extra_in_total=Money.from_rupees(extra),
    )


def test_to_offer_discovery_query_asks_for_the_product_at_its_list_price() -> None:
    """The gateway is asked about the product's own ids and list price."""
    assert build_product().to_offer_discovery_query() == OfferDiscoveryQuery(
        price=SAMPLE_PRICE,
        product_id="product-synthetic-1",
        brand_id="brand-synthetic",
        category_id="category-synthetic",
    )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("id", ""),
        ("merchant_id", ""),
        ("name", " "),
        ("gateway_product_id", ""),
        ("gateway_brand_id", ""),
        ("gateway_category_id", ""),
        ("list_price", Money.from_paise(0)),
        ("list_price", Money.from_rupees("0.001")),
        ("list_price", 2_200_000),
    ],
)
def test_catalogue_product_with_invalid_field_raises(
    field_name: str, invalid_value: object
) -> None:
    """Blank ids or name and a zero, sub-paisa or non-Money price are refused."""
    with pytest.raises(InvalidMerchantDataError):
        build_product(**{field_name: invalid_value})


def test_summarise_priced_offers_counts_plans_and_those_with_no_extra_cost() -> None:
    """Design plans A and B on ₹22,000: two plans, one with nothing extra."""
    priced_offers = [
        price_emi_offer(build_offer("plan-a", EmiType.NO_COST, "3666.67", "0"), SAMPLE_PRICE),
        price_emi_offer(build_offer("plan-b", EmiType.STANDARD, "3850", "1100"), SAMPLE_PRICE),
    ]
    assert summarise_priced_offers(priced_offers) == ProductOfferSummary(
        plan_count=2, no_extra_cost_plan_count=1
    )


def test_summarise_priced_offers_counts_a_standard_plan_with_zero_extra_as_no_extra_cost() -> None:
    """The count follows the money, not the label: zero extra is zero extra."""
    zero_extra_standard_offer = build_offer("plan-z", EmiType.STANDARD, "3666.67", "0")
    summary = summarise_priced_offers([price_emi_offer(zero_extra_standard_offer, SAMPLE_PRICE)])
    assert summary == ProductOfferSummary(plan_count=1, no_extra_cost_plan_count=1)


def test_summarise_priced_offers_with_no_offers_counts_zero() -> None:
    """A product the gateway quotes nothing for shows zero plans."""
    assert summarise_priced_offers([]) == ProductOfferSummary(
        plan_count=0, no_extra_cost_plan_count=0
    )
