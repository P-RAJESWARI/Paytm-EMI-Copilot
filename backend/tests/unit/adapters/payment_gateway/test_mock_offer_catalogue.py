"""The Mock's demo catalogue: the three M2 products get 3, 2 and 1 of the design plans."""

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_EARBUDS_PRODUCT_ID,
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiOffer, EmiType
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT, build_offer_discovery_query

SYNTHETIC_WEBHOOK_SIGNING_SECRET = bytes(range(32))


@pytest.fixture
def mock_gateway() -> MockPaymentGatewayAdapter:
    """Gives a fresh Mock on a clock that stands still."""
    return MockPaymentGatewayAdapter(FixedClock(CREATED_AT), SYNTHETIC_WEBHOOK_SIGNING_SECRET)


def build_quote(
    offer_id: str, tenure_in_months: int, monthly_in_rupees: str, extra_in_rupees: str
) -> EmiOffer:
    """Builds the offer the Mock quotes for one demo plan; the plan id fixes label and kind."""
    labels_and_kinds = {
        "mock-offer-no-cost-6m": ("Brand", EmiType.NO_COST),
        "mock-offer-card-6m": ("Your card's bank", EmiType.STANDARD),
        "mock-offer-cardless-12m": ("Demo cardless lender (Mock)", EmiType.STANDARD),
    }
    lender_label, emi_type = labels_and_kinds[offer_id]
    return EmiOffer(
        offer_id=offer_id,
        lender_label=lender_label,
        emi_type=emi_type,
        tenure_in_months=tenure_in_months,
        quoted_monthly_installment=Money.from_rupees(monthly_in_rupees),
        quoted_extra_in_total=Money.from_rupees(extra_in_rupees),
    )


@pytest.mark.parametrize(
    ("product_id", "price_in_rupees", "expected_offers"),
    [
        (
            MOCK_PHONE_128_GB_PRODUCT_ID,
            "22000",
            (
                build_quote("mock-offer-no-cost-6m", 6, "3666.67", "0"),
                build_quote("mock-offer-card-6m", 6, "3850.00", "1100"),
                build_quote("mock-offer-cardless-12m", 12, "2050.00", "2600"),
            ),
        ),
        (
            MOCK_PHONE_64_GB_PRODUCT_ID,
            "18000",
            (
                build_quote("mock-offer-no-cost-6m", 6, "3000.00", "0"),
                build_quote("mock-offer-card-6m", 6, "3150.00", "900"),
            ),
        ),
        (
            MOCK_EARBUDS_PRODUCT_ID,
            "2499",
            (build_quote("mock-offer-card-6m", 6, "437.33", "124.95"),),
        ),
    ],
    ids=["phone-128-gb-three-plans", "phone-64-gb-two-plans", "earbuds-one-card-plan"],
)
def test_mock_adapter_discover_offers_for_demo_catalogue_product_quotes_its_own_plans(
    mock_gateway: MockPaymentGatewayAdapter,
    product_id: str,
    price_in_rupees: str,
    expected_offers: tuple[EmiOffer, ...],
) -> None:
    """The three M2 products get 3, 2 and 1 plans, each priced by the same demo rule."""
    query = build_offer_discovery_query(
        product_id=product_id, price=Money.from_rupees(price_in_rupees)
    )
    assert mock_gateway.discover_offers(query) == expected_offers
