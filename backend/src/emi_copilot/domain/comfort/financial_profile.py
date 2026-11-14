"""FinancialProfile: the monthly figures a comfort check reads, after the customer consents."""

from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidComfortInputError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import (
    require_positive_whole_paise_money,
    require_whole_paise_money,
)


@dataclass(frozen=True, slots=True)
class FinancialProfile:
    """A customer's monthly inflow and the EMIs they already pay each month.

    Synthetic in the hackathon build (ADR 0020 decision 6). In production only these derived
    monthly figures would be held, never raw statements (security-and-compliance.md section 2).
    The merchant never sees them (CLAUDE.md section 2, rule 6).
    """

    monthly_inflow: Money
    existing_emis_per_month: Money

    def __post_init__(self) -> None:
        """Refuses an inflow that is not positive whole paise and sub-paise existing EMIs."""
        require_positive_whole_paise_money(
            self.monthly_inflow, "monthly inflow", InvalidComfortInputError
        )
        require_whole_paise_money(
            self.existing_emis_per_month, "existing EMIs per month", InvalidComfortInputError
        )
