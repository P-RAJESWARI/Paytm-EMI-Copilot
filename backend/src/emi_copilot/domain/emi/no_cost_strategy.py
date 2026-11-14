"""No-cost EMI: the customer pays back exactly the principal."""

from emi_copilot.domain.emi.emi_calculation_strategy import EmiCalculationStrategy
from emi_copilot.domain.emi.emi_schedule import EmiSchedule, split_total_payable_evenly
from emi_copilot.domain.money import Money


class NoCostStrategy(EmiCalculationStrategy):
    """Splits the principal evenly, so the extra in total is exactly zero (ADR 0001, plan A)."""

    def calculate_schedule(self, principal: Money, tenure_in_months: int) -> EmiSchedule:
        """Calculates a schedule whose total payable equals the principal."""
        return split_total_payable_evenly(principal, tenure_in_months, total_payable=principal)
