"""PlanAlternative and PlanAlternatives: C6's options beside the chosen plan, all recomputed."""

from dataclasses import dataclass

from emi_copilot.domain.alternatives.alternative_kind import AlternativeKind
from emi_copilot.domain.alternatives.cheaper_model_quote import CheaperModelQuote
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.ranking import BudgetFit, calculate_monthly_commitment

_ZERO_RUPEES = Money.from_paise(0)


@dataclass(frozen=True, slots=True)
class PlanAlternative:
    """One alternative: its plan, budget fit and the chosen plan's monthly commitment ("was").

    Build it with the for_* constructors, which keep the down payment and product fields
    consistent with the kind. It is kept even when it does not lower the monthly amount.
    """

    kind: AlternativeKind
    priced_offer: PricedEmiOffer
    down_payment: Money
    product_id: str | None
    product_name: str | None
    previous_monthly_commitment: Money
    budget_fit: BudgetFit

    @classmethod
    def for_down_payment(
        cls,
        priced_offer: PricedEmiOffer,
        down_payment: Money,
        previous_monthly_commitment: Money,
        monthly_budget: Money,
    ) -> "PlanAlternative":
        """Builds the chosen plan re-quoted on the price less the down payment."""
        return cls(
            kind=AlternativeKind.DOWN_PAYMENT,
            priced_offer=priced_offer,
            down_payment=down_payment,
            product_id=None,
            product_name=None,
            previous_monthly_commitment=previous_monthly_commitment,
            budget_fit=BudgetFit(monthly_budget, calculate_monthly_commitment(priced_offer)),
        )

    @classmethod
    def for_longer_tenure(
        cls, priced_offer: PricedEmiOffer, previous_monthly_commitment: Money, monthly_budget: Money
    ) -> "PlanAlternative":
        """Builds another plan for the same item that runs for more months."""
        return cls(
            kind=AlternativeKind.LONGER_TENURE,
            priced_offer=priced_offer,
            down_payment=_ZERO_RUPEES,
            product_id=None,
            product_name=None,
            previous_monthly_commitment=previous_monthly_commitment,
            budget_fit=BudgetFit(monthly_budget, calculate_monthly_commitment(priced_offer)),
        )

    @classmethod
    def for_cheaper_model(
        cls,
        priced_offer: PricedEmiOffer,
        cheaper_model: CheaperModelQuote,
        previous_monthly_commitment: Money,
        monthly_budget: Money,
    ) -> "PlanAlternative":
        """Builds a plan on a cheaper model, naming that model."""
        return cls(
            kind=AlternativeKind.CHEAPER_MODEL,
            priced_offer=priced_offer,
            down_payment=_ZERO_RUPEES,
            product_id=cheaper_model.product_id,
            product_name=cheaper_model.product_name,
            previous_monthly_commitment=previous_monthly_commitment,
            budget_fit=BudgetFit(monthly_budget, calculate_monthly_commitment(priced_offer)),
        )

    @property
    def monthly_commitment(self) -> Money:
        """Gives this alternative's largest single installment."""
        return self.budget_fit.monthly_commitment

    @property
    def is_lower_monthly_amount(self) -> bool:
        """Tells whether this alternative asks less each month than the chosen plan."""
        return self.monthly_commitment < self.previous_monthly_commitment


@dataclass(frozen=True, slots=True)
class PlanAlternatives:
    """The chosen plan and every alternative found for it, in C6 order."""

    chosen_plan: PricedEmiOffer
    alternatives: tuple[PlanAlternative, ...]

    @property
    def has_lower_monthly_alternative(self) -> bool:
        """Tells whether any alternative lowers the monthly amount; False is C6 "nothing better"."""
        return any(alternative.is_lower_monthly_amount for alternative in self.alternatives)
