"""BudgetFit: how a plan's monthly commitment compares with the customer's monthly budget."""

from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidMonthlyBudgetError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import require_positive_whole_paise_money

_ZERO_RUPEES = Money.from_paise(0)


def require_valid_monthly_budget(monthly_budget: object) -> None:
    """Raises InvalidMonthlyBudgetError unless the budget is whole-paise Money above zero."""
    require_positive_whole_paise_money(monthly_budget, "monthly budget", InvalidMonthlyBudgetError)


# Pattern: Value Object. Budget and commitment travel together, so "how far above" has one answer.
@dataclass(frozen=True, slots=True)
class BudgetFit:
    """A plan fits when its monthly commitment is at or below the budget; equal counts as within."""

    monthly_budget: Money
    monthly_commitment: Money

    def __post_init__(self) -> None:
        """Refuses an invalid budget and a commitment that is not Money."""
        require_valid_monthly_budget(self.monthly_budget)
        if not isinstance(self.monthly_commitment, Money):
            raise InvalidMonthlyBudgetError("The monthly commitment must be Money.")

    @property
    def is_within_budget(self) -> bool:
        """Tells whether the monthly commitment is at or below the monthly budget."""
        return self.monthly_commitment <= self.monthly_budget

    @property
    def amount_above_budget(self) -> Money:
        """Gives how much the commitment exceeds the budget each month; zero when within it."""
        if self.is_within_budget:
            return _ZERO_RUPEES
        return self.monthly_commitment - self.monthly_budget
