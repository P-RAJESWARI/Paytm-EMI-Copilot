"""Builders of priced design plans (DESIGN_SPEC.md section 4) for ranking and alternatives tests.

Each offer is quoted the way the Mock gateway quotes it: the lender's monthly figure is the
engine's regular installment, so quote and schedule agree. Offer ids match the Mock catalogue.
"""

from emi_copilot.domain.emi import NoCostStrategy, QuotedTotalStrategy
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiOffer, EmiType, PricedEmiOffer, price_emi_offer

SAMPLE_PRICE = Money.from_rupees("22000")
CHEAPER_MODEL_PRICE = Money.from_rupees("18000")
NO_COST_OFFER_ID = "mock-offer-no-cost-6m"
CARD_OFFER_ID = "mock-offer-card-6m"
CARDLESS_OFFER_ID = "mock-offer-cardless-12m"


def build_priced_plan(
    offer_id: str,
    tenure_in_months: int,
    extra_in_total: Money,
    price: Money,
    quoted_monthly_installment: Money | None = None,
) -> PricedEmiOffer:
    """Prices a plan; no extra means no-cost, and the quote defaults to the engine's figure."""
    emi_type = EmiType.NO_COST if extra_in_total.is_zero else EmiType.STANDARD
    if quoted_monthly_installment is None:
        strategy = (
            NoCostStrategy() if extra_in_total.is_zero else QuotedTotalStrategy(extra_in_total)
        )
        quoted_monthly_installment = strategy.calculate_schedule(
            price, tenure_in_months
        ).regular_installment
    offer = EmiOffer(
        offer_id=offer_id,
        lender_label=f"Lender of {offer_id}",
        emi_type=emi_type,
        tenure_in_months=tenure_in_months,
        quoted_monthly_installment=quoted_monthly_installment,
        quoted_extra_in_total=extra_in_total,
    )
    return price_emi_offer(offer, price)


def build_no_cost_plan_a(price: Money = SAMPLE_PRICE) -> PricedEmiOffer:
    """Design plan A: no-cost over 6 months (₹3,666.67 a month on ₹22,000)."""
    return build_priced_plan(NO_COST_OFFER_ID, 6, Money.from_paise(0), price)


def build_card_plan_b() -> PricedEmiOffer:
    """Design plan B on ₹22,000: 6 x ₹3,850.00 with ₹1,100 extra in total."""
    return build_priced_plan(CARD_OFFER_ID, 6, Money.from_rupees("1100"), SAMPLE_PRICE)


def build_cardless_plan_c() -> PricedEmiOffer:
    """Design plan C on ₹22,000: 12 x ₹2,050.00 with ₹2,600 extra in total."""
    return build_priced_plan(CARDLESS_OFFER_ID, 12, Money.from_rupees("2600"), SAMPLE_PRICE)


def build_design_plans() -> tuple[PricedEmiOffer, PricedEmiOffer, PricedEmiOffer]:
    """Gives design plans A, B and C on ₹22,000, in catalogue order."""
    return (build_no_cost_plan_a(), build_card_plan_b(), build_cardless_plan_c())
