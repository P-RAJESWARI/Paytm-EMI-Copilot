"""DownPaymentRule: the down payment that brings a plan near the budget (ADR 0020 decision 2)."""

from emi_copilot.domain.emi import require_valid_emi_terms
from emi_copilot.domain.errors import InvalidMoneyAmountError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import require_positive_whole_paise_money
from emi_copilot.domain.ranking import require_valid_monthly_budget

DEFAULT_DOWN_PAYMENT_ROUNDING_STEP = Money.from_rupees(1000)
"""Down payments are suggested in whole ₹1,000 steps; the one place this value is held."""


class DownPaymentRule:
    """Derives the down payment from the price, the budget and the chosen tenure; never configured.

    D = price - budget x tenure, rounded up to the next rounding step. There is no suggestion when
    the budget already covers the price or when D would be the whole price or more.
    """

    def __init__(self, rounding_step: Money = DEFAULT_DOWN_PAYMENT_ROUNDING_STEP) -> None:
        """Stores the rounding step, which must be whole-paise Money above zero."""
        require_positive_whole_paise_money(
            rounding_step, "down-payment rounding step", InvalidMoneyAmountError
        )
        self._rounding_step = rounding_step

    def suggest_down_payment(
        self, price: Money, monthly_budget: Money, tenure_in_months: int
    ) -> Money | None:
        """Gives the rounded-up down payment, or None when none is needed or none could help."""
        require_valid_emi_terms(price, tenure_in_months)
        require_valid_monthly_budget(monthly_budget)
        amount_covered_by_budget = monthly_budget * tenure_in_months
        # Money is never negative, so compare before subtracting.
        if amount_covered_by_budget >= price:
            return None
        gap_in_paise = (price - amount_covered_by_budget).to_paise()
        whole_steps, remainder_in_paise = divmod(gap_in_paise, self._rounding_step.to_paise())
        step_count = whole_steps + (1 if remainder_in_paise else 0)
        down_payment = self._rounding_step * step_count
        if down_payment >= price:
            return None
        return down_payment
