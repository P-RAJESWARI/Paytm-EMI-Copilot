"""Inputs and results of PlanAdviceService: what C4 and C6 show, before it becomes wire DTOs."""

from dataclasses import dataclass
from typing import Protocol

from emi_copilot.domain.alternatives import PlanAlternative
from emi_copilot.domain.comfort import ComfortAssessment
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery, PricedEmiOffer
from emi_copilot.domain.ranking import BudgetFit, PlanRanking, RankedPlan


class PricedOfferSource(Protocol):
    """Anything that gives every plan quoted for an item, each priced by the EMI engine.

    The Layer 1 OfferDiscoveryService satisfies it, and is what Phase 3C wires in.
    """

    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[PricedEmiOffer, ...]:
        """Gives every plan quoted for the item at its price, priced by the engine."""
        ...


@dataclass(frozen=True, slots=True)
class CheaperModelCandidate:
    """A cheaper catalogue item to quote as a C6 alternative; the catalogue belongs to Layer 2."""

    product_id: str
    product_name: str
    price: Money
    brand_id: str
    category_id: str

    def to_offer_discovery_query(self) -> OfferDiscoveryQuery:
        """Gives the query that asks for this model's plans at its price."""
        return OfferDiscoveryQuery(
            price=self.price,
            product_id=self.product_id,
            brand_id=self.brand_id,
            category_id=self.category_id,
        )


@dataclass(frozen=True, slots=True)
class AdvisedPlan:
    """One ranked plan with its comfort assessment; None when the comfort check was skipped."""

    ranked_plan: RankedPlan
    comfort: ComfortAssessment | None


@dataclass(frozen=True, slots=True)
class PlanComparison:
    """Every quoted plan in C4 order; none is dropped, even when none fits the budget."""

    ranking: PlanRanking
    advised_plans: tuple[AdvisedPlan, ...]
    has_comfort_check: bool


@dataclass(frozen=True, slots=True)
class AdvisedAlternative:
    """One C6 alternative with its comfort assessment; None when the comfort check was skipped."""

    alternative: PlanAlternative
    comfort: ComfortAssessment | None


@dataclass(frozen=True, slots=True)
class AlternativesAdvice:
    """The chosen plan with its fit and comfort, and every alternative found for it."""

    chosen_plan: PricedEmiOffer
    chosen_plan_budget_fit: BudgetFit
    chosen_plan_comfort: ComfortAssessment | None
    advised_alternatives: tuple[AdvisedAlternative, ...]
    has_lower_monthly_alternative: bool
