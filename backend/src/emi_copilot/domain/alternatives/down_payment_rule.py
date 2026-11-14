"""DownPaymentRule: the down payment that brings a plan near the budget (ADR 0020 decision 2)."""

from emi_copilot.domain.errors import InvalidMoneyAmountError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.payments.field_validation import require_positive_whole_paise_money
from emi_copilot.domain.ranking import require_valid_monthly_budget

DEFAULT_DOWN_PAYMENT_ROUNDING_STEP = Money.from_rupees(1000)
"""Down payments are suggested in whole ₹1,000 steps; the one place this value is held."""


class DownPaymentRule:
    """Derives the down payment from the chosen plan and the budget; never configured.

    D = the plan's total payable - budget x tenure, rounded up to the next rounding step, so a
    plan with an extra cost is judged on what it really collects (ADR 0020 decision 2). There is
    no suggestion when the budget already covers the total or when D would be the whole price or
    more. The plan re-quoted on price - D is shown honestly, even if it is still above budget.
    """

    def __init__(self, rounding_step: Money = DEFAULT_DOWN_PAYMENT_ROUNDING_STEP) -> None:
        """Stores the rounding step, which must be whole-paise Money above zero."""
        require_positive_whole_paise_money(
            rounding_step, "down-payment rounding step", InvalidMoneyAmountError
        )
        self._rounding_step = rounding_step

    def suggest_down_payment(
        self, chosen_plan: PricedEmiOffer, monthly_budget: Money
    ) -> Money | None:
        """Gives the rounded-up down payment, or None when none is needed or none could help."""
        require_valid_monthly_budget(monthly_budget)
        schedule = chosen_plan.schedule
        amount_covered_by_budget = monthly_budget * schedule.tenure_in_months
        # Money is never negative, so compare before subtracting.
        if amount_covered_by_budget >= schedule.total_payable:
            return None
        gap_in_paise = (schedule.total_payable - amount_covered_by_budget).to_paise()
        whole_steps, remainder_in_paise = divmod(gap_in_paise, self._rounding_step.to_paise())
        step_count = whole_steps + (1 if remainder_in_paise else 0)
        down_payment = self._rounding_step * step_count
        if down_payment >= schedule.principal:
            return None
        return down_payment
