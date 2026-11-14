"""The interface every EMI calculation rule implements."""

from abc import ABC, abstractmethod

from emi_copilot.domain.emi.emi_schedule import EmiSchedule
from emi_copilot.domain.money import Money


# Pattern: Strategy. No-cost, quoted-total and reducing-balance rules vary independently of callers.
class EmiCalculationStrategy(ABC):
    """Turns a principal and a tenure into an EmiSchedule under one lender pricing rule.

    Rounding rule, shared by every strategy: compute exactly, round the regular installment once,
    half-up to the paisa, and let the last installment absorb the remainder so that the
    installments sum to the total payable exactly, to the paisa. The principal must be positive
    whole-paise Money and the tenure at least one month (InvalidEmiTermsError otherwise). If the
    rounded regular installments alone would exceed the total, so that the last one would be
    negative, EmiScheduleNotRepresentableError is raised instead of returning a wrong schedule.
    """

    @abstractmethod
    def calculate_schedule(self, principal: Money, tenure_in_months: int) -> EmiSchedule:
        """Calculates the installment schedule for this pricing rule."""
