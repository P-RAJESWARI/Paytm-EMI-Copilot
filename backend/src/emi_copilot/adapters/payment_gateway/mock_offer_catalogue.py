"""The Mock gateway's demo pricing rule: design plans A, B and C scaled to any price (mock-only)."""

from dataclasses import dataclass

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


MOCK_PLAN_DEFINITIONS = (
    _MockPlanDefinition(
        offer_id="mock-offer-no-cost-6m",
        lender_label="Brand",
        emi_type=EmiType.NO_COST,
        tenure_in_months=6,
        extra_numerator=0,
        extra_denominator=1,
    ),
    _MockPlanDefinition(
        offer_id="mock-offer-card-6m",
        lender_label="Your card's bank",
        emi_type=EmiType.STANDARD,
        tenure_in_months=6,
        extra_numerator=5,
        extra_denominator=100,
    ),
    _MockPlanDefinition(
        offer_id="mock-offer-cardless-12m",
        lender_label="Demo cardless lender (Mock)",
        emi_type=EmiType.STANDARD,
        tenure_in_months=12,
        extra_numerator=_CARDLESS_PLAN_EXTRA_IN_RUPEES_AT_SAMPLE_PRICE,
        extra_denominator=_SAMPLE_PRICE_IN_RUPEES,
    ),
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


def quote_mock_offers(price: Money) -> tuple[EmiOffer, ...]:
    """Quotes design plans A, B and C on the price; a price out of range for EMI is refused.

    A price so small that an installment would round to zero paise or cannot be split into
    non-negative installments, or so large that its total no longer fits in Money, is refused
    the way a real gateway refuses an out-of-range amount.
    """
    try:
        return tuple(_quote_mock_plan(price, plan) for plan in MOCK_PLAN_DEFINITIONS)
    except (
        EmiScheduleNotRepresentableError,
        InvalidMoneyAmountError,
        InvalidPaymentGatewayValueError,
    ) as error:
        raise PaymentGatewayRequestRejectedError(
            PaymentGatewayRejectionReason.INVALID_REQUEST,
            f"The mock gateway cannot quote EMI on a price of {price} rupees.",
        ) from error
