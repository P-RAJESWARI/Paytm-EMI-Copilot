"""The Mock gateway's demo pricing rule: design plans A, B and C scaled to any price (mock-only).

Three demo catalogue products (DESIGN_SPEC M2) get their own subset of those plans, so the
counter list shows "3 EMI plans", "2 EMI plans" and "1 EMI plan". Every other product id gets
all three plans, as in Layer 1.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from emi_copilot.domain.emi import NoCostStrategy, QuotedTotalStrategy
from emi_copilot.domain.errors import (
    EmiScheduleNotRepresentableError,
    InvalidMoneyAmountError,
    InvalidPaymentGatewayValueError,
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiOffer, EmiType

# Design plan B charges 5% of the price; plan C charges what it does on the ₹22,000 sample item
# (₹2,600) in proportion to the price. Demo rules only; no lender publishes them (ADR 0002). Each
# extra is kept as an integer ratio, so price x numerator / denominator is exact before rounding.
_CARDLESS_PLAN_EXTRA_IN_RUPEES_AT_SAMPLE_PRICE = 2600
_SAMPLE_PRICE_IN_RUPEES = 22000


@dataclass(frozen=True, slots=True)
class _MockPlanDefinition:
    """One demo plan: its stable offer id, ADR 0002 label, pricing kind, tenure and extra ratio."""

    offer_id: str
    lender_label: str
    emi_type: EmiType
    tenure_in_months: int
    extra_numerator: int
    extra_denominator: int


_NO_COST_SIX_MONTH_PLAN = _MockPlanDefinition(
    offer_id="mock-offer-no-cost-6m",
    lender_label="Brand",
    emi_type=EmiType.NO_COST,
    tenure_in_months=6,
    extra_numerator=0,
    extra_denominator=1,
)
_CARD_SIX_MONTH_PLAN = _MockPlanDefinition(
    offer_id="mock-offer-card-6m",
    lender_label="Your card's bank",
    emi_type=EmiType.STANDARD,
    tenure_in_months=6,
    extra_numerator=5,
    extra_denominator=100,
)
_CARDLESS_TWELVE_MONTH_PLAN = _MockPlanDefinition(
    offer_id="mock-offer-cardless-12m",
    lender_label="Demo cardless lender (Mock)",
    emi_type=EmiType.STANDARD,
    tenure_in_months=12,
    extra_numerator=_CARDLESS_PLAN_EXTRA_IN_RUPEES_AT_SAMPLE_PRICE,
    extra_denominator=_SAMPLE_PRICE_IN_RUPEES,
)

MOCK_PLAN_DEFINITIONS = (_NO_COST_SIX_MONTH_PLAN, _CARD_SIX_MONTH_PLAN, _CARDLESS_TWELVE_MONTH_PLAN)
"""Plans A, B and C: what the Mock quotes for any product outside the demo catalogue."""

# Demo catalogue product ids (mock-only, labelled as such); the demo seed stores these on its
# products. At their seeded prices: the 128 GB phone (₹22,000) gets plans A, B and C; the 64 GB
# phone (₹18,000) gets A (6 x ₹3,000, nothing extra) and B (6 x ₹3,150, ₹900 extra); the
# earbuds (₹2,499) get B only (₹124.95 extra over 6 months).
MOCK_PHONE_128_GB_PRODUCT_ID = "mock-product-phone-128gb"
MOCK_PHONE_64_GB_PRODUCT_ID = "mock-product-phone-64gb"
MOCK_EARBUDS_PRODUCT_ID = "mock-product-earbuds"

MOCK_PLAN_DEFINITIONS_BY_PRODUCT_ID: Mapping[str, tuple[_MockPlanDefinition, ...]] = (
    MappingProxyType(
        {
            MOCK_PHONE_128_GB_PRODUCT_ID: MOCK_PLAN_DEFINITIONS,
            MOCK_PHONE_64_GB_PRODUCT_ID: (_NO_COST_SIX_MONTH_PLAN, _CARD_SIX_MONTH_PLAN),
            MOCK_EARBUDS_PRODUCT_ID: (_CARD_SIX_MONTH_PLAN,),
        }
    )
)


def _calculate_quoted_extra_in_total(price: Money, plan: _MockPlanDefinition) -> Money:
    """Gives the plan's extra cost on the price, rounded half-up to the paisa exactly once."""
    return (price * plan.extra_numerator / plan.extra_denominator).rounded_to_paise()


def _quote_mock_plan(price: Money, plan: _MockPlanDefinition) -> EmiOffer:
    """Quotes one demo plan the way a lender would: a monthly installment and an extra in total."""
    quoted_extra_in_total = _calculate_quoted_extra_in_total(price, plan)
    if plan.emi_type is EmiType.NO_COST:
        schedule = NoCostStrategy().calculate_schedule(price, plan.tenure_in_months)
    else:
        schedule = QuotedTotalStrategy(quoted_extra_in_total).calculate_schedule(
            price, plan.tenure_in_months
        )
    return EmiOffer(
        offer_id=plan.offer_id,
        lender_label=plan.lender_label,
        emi_type=plan.emi_type,
        tenure_in_months=plan.tenure_in_months,
        quoted_monthly_installment=schedule.regular_installment,
        quoted_extra_in_total=quoted_extra_in_total,
    )


def quote_mock_offers(price: Money, product_id: str) -> tuple[EmiOffer, ...]:
    """Quotes the product's demo plans on the price; a price out of range for EMI is refused.

    A demo catalogue product gets its own plans; any other product gets plans A, B and C. A
    price so small that an installment would round to zero paise or cannot be split into
    non-negative installments, or so large that its total no longer fits in Money, is refused
    the way a real gateway refuses an out-of-range amount.
    """
    try:
        plans = MOCK_PLAN_DEFINITIONS_BY_PRODUCT_ID.get(product_id, MOCK_PLAN_DEFINITIONS)
        return tuple(_quote_mock_plan(price, plan) for plan in plans)
    except (
        EmiScheduleNotRepresentableError,
        InvalidMoneyAmountError,
        InvalidPaymentGatewayValueError,
    ) as error:
        raise PaymentGatewayRequestRejectedError(
            PaymentGatewayRejectionReason.INVALID_REQUEST,
            f"The mock gateway cannot quote EMI on a price of {price} rupees.",
        ) from error
