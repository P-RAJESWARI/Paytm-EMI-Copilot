"""ProductOfferSummary: how many EMI plans a product has, and how many cost nothing extra."""

from collections.abc import Iterable
from dataclasses import dataclass

from emi_copilot.domain.payments import PricedEmiOffer


# Pattern: Value Object. The counter list's one-line offer summary, counted from priced offers.
@dataclass(frozen=True, slots=True)
class ProductOfferSummary:
    """Counts for "3 EMI plans, 1 with no extra cost"; the words are the frontend's job."""

    plan_count: int
    no_extra_cost_plan_count: int


def summarise_priced_offers(priced_offers: Iterable[PricedEmiOffer]) -> ProductOfferSummary:
    """Counts every offer, and those whose schedule adds nothing to the price.

    The count uses our schedule's extra in total, not the offer's label, so a standard plan that
    happens to cost nothing extra counts too.
    """
    offers = tuple(priced_offers)
    return ProductOfferSummary(
        plan_count=len(offers),
        no_extra_cost_plan_count=sum(
            1 for offer in offers if offer.schedule.extra_in_total.is_zero
        ),
    )
