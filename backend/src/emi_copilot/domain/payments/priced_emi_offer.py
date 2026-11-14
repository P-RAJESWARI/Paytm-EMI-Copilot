"""PricedEmiOffer: a lender's quote beside the schedule our engine builds from it (ADR 0001)."""

from dataclasses import dataclass

from emi_copilot.domain.emi import EmiSchedule, NoCostStrategy, QuotedTotalStrategy
from emi_copilot.domain.emi.emi_calculation_strategy import EmiCalculationStrategy
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.emi_offer import EmiOffer
from emi_copilot.domain.payments.emi_type import EmiType
from emi_copilot.domain.payments.offer_snapshot import OfferSnapshot

QUOTE_MISMATCH_TOLERANCE = Money.from_rupees("1")
"""ADR 0001: a gap above ₹1 per installment between quote and schedule is audited."""


# Pattern: Value Object. The quote and our schedule travel together, so neither is shown alone.
@dataclass(frozen=True, slots=True)
class PricedEmiOffer:
    """An offer as quoted plus our schedule on the price; the lender's monthly figure is shown.

    The schedule gives the totals: it splits price plus quoted extra exactly to the paisa, with
    the remainder on the last installment.
    """

    offer: EmiOffer
    schedule: EmiSchedule

    def __post_init__(self) -> None:
        """Rejects a schedule over a different tenure than the offer's."""
        if self.schedule.tenure_in_months != self.offer.tenure_in_months:
            raise InvalidPaymentGatewayValueError("The schedule must cover the offer's tenure.")

    @property
    def quoted_monthly_installment(self) -> Money:
        """Gives the lender's monthly figure, which is what the customer is shown."""
        return self.offer.quoted_monthly_installment

    @property
    def quote_difference(self) -> Money:
        """Gives how far the lender's monthly figure is from our regular installment."""
        quoted_installment = self.offer.quoted_monthly_installment
        regular_installment = self.schedule.regular_installment
        if quoted_installment >= regular_installment:
            return quoted_installment - regular_installment
        return regular_installment - quoted_installment

    @property
    def has_quote_mismatch(self) -> bool:
        """Tells whether quote and schedule differ by more than ₹1 per installment."""
        return self.quote_difference > QUOTE_MISMATCH_TOLERANCE

    def to_offer_snapshot(self) -> OfferSnapshot:
        """Freezes the plan as evidence: the lender's labels with our exact schedule amounts."""
        return OfferSnapshot(
            offer_id=self.offer.offer_id,
            lender_label=self.offer.lender_label,
            emi_type=self.offer.emi_type,
            tenure_in_months=self.offer.tenure_in_months,
            regular_installment=self.schedule.regular_installment,
            last_installment=self.schedule.last_installment,
            total_payable=self.schedule.total_payable,
            extra_in_total=self.schedule.extra_in_total,
        )


def select_strategy_for_offer(offer: EmiOffer) -> EmiCalculationStrategy:
    """Gives NoCostStrategy for a no-cost offer and QuotedTotalStrategy for every other one."""
    if offer.emi_type is EmiType.NO_COST:
        return NoCostStrategy()
    return QuotedTotalStrategy(offer.quoted_extra_in_total)


def price_emi_offer(offer: EmiOffer, price: Money) -> PricedEmiOffer:
    """Builds the schedule for an offer on the item price and pairs it with the quote."""
    schedule = select_strategy_for_offer(offer).calculate_schedule(price, offer.tenure_in_months)
    return PricedEmiOffer(offer=offer, schedule=schedule)
