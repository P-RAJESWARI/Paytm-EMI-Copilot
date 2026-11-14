"""Tests for PricedEmiOffer: the quote beside our exact schedule, and the ₹1 mismatch check."""

import pytest

from emi_copilot.domain.emi import NoCostStrategy, QuotedTotalStrategy
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType, PricedEmiOffer, price_emi_offer
from emi_copilot.domain.payments.priced_emi_offer import select_strategy_for_offer
from tests.payment_builders import (
    build_emi_offer,
    build_no_cost_offer_snapshot,
    build_standard_offer_snapshot,
)

PRICE = Money.from_rupees("22000")


def _build_no_cost_offer_a() -> PricedEmiOffer:
    """Prices design plan A, quoted at ₹3,666.67 a month with no extra."""
    offer = build_emi_offer(
        offer_id="offer-plan-a",
        lender_label="Brand",
        emi_type=EmiType.NO_COST,
        quoted_monthly_installment=Money.from_rupees("3666.67"),
        quoted_extra_in_total=Money.from_paise(0),
    )
    return price_emi_offer(offer, PRICE)


def test_price_emi_offer_for_a_no_cost_offer_splits_the_price_with_nothing_extra() -> None:
    """Plan A: 5 x ₹3,666.67 then ₹3,666.65, and its snapshot is the design snapshot."""
    priced_offer = _build_no_cost_offer_a()
    assert priced_offer.schedule.regular_installment == Money.from_rupees("3666.67")
    assert priced_offer.schedule.last_installment == Money.from_rupees("3666.65")
    assert priced_offer.to_offer_snapshot() == build_no_cost_offer_snapshot()
    assert not priced_offer.has_quote_mismatch


def test_price_emi_offer_for_a_standard_offer_adds_the_quoted_extra() -> None:
    """Plan B: ₹22,000 plus ₹1,100 is exactly 6 x ₹3,850.00; the quote shown is the lender's."""
    priced_offer = price_emi_offer(build_emi_offer(), PRICE)
    assert priced_offer.to_offer_snapshot() == build_standard_offer_snapshot()
    assert priced_offer.quoted_monthly_installment == Money.from_rupees("3850.00")
    assert priced_offer.quote_difference == Money.from_paise(0)


def test_select_strategy_for_offer_uses_no_cost_only_for_no_cost_offers() -> None:
    """NO_COST gets NoCostStrategy; every other offer is priced by its quoted extra."""
    assert isinstance(select_strategy_for_offer(_build_no_cost_offer_a().offer), NoCostStrategy)
    standard_strategy = select_strategy_for_offer(build_emi_offer())
    assert isinstance(standard_strategy, QuotedTotalStrategy)
    assert standard_strategy.quoted_extra_in_total == Money.from_rupees("1100")


@pytest.mark.parametrize(
    ("quoted_monthly_installment", "expected_mismatch"),
    [
        ("3851.00", False),
        ("3849.00", False),
        ("3851.01", True),
        ("3848.99", True),
    ],
)
def test_price_emi_offer_flags_a_quote_more_than_one_rupee_from_the_schedule(
    quoted_monthly_installment: str, *, expected_mismatch: bool
) -> None:
    """Exactly ₹1 apart is tolerated in either direction; one paisa more is a mismatch."""
    offer = build_emi_offer(
        quoted_monthly_installment=Money.from_rupees(quoted_monthly_installment)
    )
    priced_offer = price_emi_offer(offer, PRICE)
    assert priced_offer.has_quote_mismatch is expected_mismatch
    assert priced_offer.quoted_monthly_installment == Money.from_rupees(quoted_monthly_installment)


def test_priced_emi_offer_with_a_schedule_of_another_tenure_raises() -> None:
    """The schedule must belong to the offer it is shown with."""
    twelve_month_schedule = NoCostStrategy().calculate_schedule(PRICE, 12)
    with pytest.raises(InvalidPaymentGatewayValueError, match="tenure"):
        PricedEmiOffer(offer=build_emi_offer(), schedule=twelve_month_schedule)
