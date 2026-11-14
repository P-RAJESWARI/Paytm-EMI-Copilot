"""EdcInstructions: what the merchant keys into the card machine (EDC) for an agreed plan (M4).

Instructions only (plan Q5): the server cannot see an EDC payment, so nothing here marks a sale
paid; PAID still comes only from a verified gateway report.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales.chosen_plan import ChosenPlan


class EdcEmiProgramme(StrEnum):
    """Which EMI menu to choose on the card machine."""

    BRAND_EMI = "BRAND_EMI"
    """The brand funds the cost, so the customer pays nothing extra."""

    BANK_EMI = "BANK_EMI"
    """The card's bank charges the extra cost shown on the plan."""


EDC_EMI_PROGRAMME_BY_PLAN_KIND: Mapping[EmiType, EdcEmiProgramme] = MappingProxyType(
    {EmiType.NO_COST: EdcEmiProgramme.BRAND_EMI, EmiType.STANDARD: EdcEmiProgramme.BANK_EMI}
)
"""One row per plan kind, so a new kind cannot reach the counter without a decision."""


# Pattern: Value Object. The steps M4 shows next to the agreed plan, derived in one place.
@dataclass(frozen=True, slots=True)
class EdcInstructions:
    """Choose this EMI menu, pick this product and tenure, and check this amount."""

    emi_programme: EdcEmiProgramme
    product_name: str
    tenure_in_months: int
    is_no_extra_cost: bool
    amount: Money

    @classmethod
    def for_chosen_plan(cls, chosen_plan: ChosenPlan, product_name: str) -> "EdcInstructions":
        """Derives the steps from the agreed plan; the amount is the item price, not the total."""
        return cls(
            emi_programme=EDC_EMI_PROGRAMME_BY_PLAN_KIND[chosen_plan.plan_kind],
            product_name=product_name,
            tenure_in_months=chosen_plan.tenure_in_months,
            is_no_extra_cost=chosen_plan.extra_in_total.is_zero,
            amount=chosen_plan.price,
        )
