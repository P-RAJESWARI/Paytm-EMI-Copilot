"""Quoted-total EMI: the lender states the extra cost and we split principal plus extra evenly."""

from emi_copilot.domain.emi.emi_calculation_strategy import EmiCalculationStrategy
from emi_copilot.domain.emi.emi_schedule import (
    EmiSchedule,
    require_valid_emi_terms,
    split_total_payable_evenly,
)
from emi_copilot.domain.errors import InvalidEmiTermsError
from emi_copilot.domain.money import Money


class QuotedTotalStrategy(EmiCalculationStrategy):
    """Charges exactly the lender's quoted extra; used for design plans B and C and gateway offers.

    ADR 0001: no annual rate reproduces the design figures exactly, but a quoted extra does.
    """

    def __init__(self, quoted_extra_in_total: Money) -> None:
        """Stores the lender's quoted extra cost, which must be whole-paise Money (zero allowed)."""
        if not isinstance(quoted_extra_in_total, Money) or not quoted_extra_in_total.is_whole_paise:
            raise InvalidEmiTermsError("The quoted extra in total must be Money in whole paise.")
        self._quoted_extra_in_total = quoted_extra_in_total

    @property
    def quoted_extra_in_total(self) -> Money:
        """Gives the lender's quoted extra cost over the whole plan."""
        return self._quoted_extra_in_total

    def calculate_schedule(self, principal: Money, tenure_in_months: int) -> EmiSchedule:
        """Calculates a schedule whose total payable is the principal plus the quoted extra."""
        require_valid_emi_terms(principal, tenure_in_months)
        return split_total_payable_evenly(
            principal, tenure_in_months, total_payable=principal + self._quoted_extra_in_total
        )
