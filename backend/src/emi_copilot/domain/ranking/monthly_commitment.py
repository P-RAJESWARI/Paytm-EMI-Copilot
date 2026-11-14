"""The monthly amount a plan commits the customer to, for budget fit and the comfort ratio."""

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer


def calculate_monthly_commitment(priced_offer: PricedEmiOffer) -> Money:
    """Gives the largest single installment: the lender's quote, our regular or our last one.

    ADR 0020 decision 3: judging a plan on its largest month is conservative, and on the design
    data it equals the monthly amount shown.
    """
    schedule = priced_offer.schedule
    return max(
        priced_offer.quoted_monthly_installment,
        schedule.regular_installment,
        schedule.last_installment,
    )
