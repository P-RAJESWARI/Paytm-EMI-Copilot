"""FinancialProfilePort: where a consented comfort check reads a customer's monthly figures."""

from abc import ABC, abstractmethod

from emi_copilot.domain.comfort import FinancialProfile


# Pattern: Port and Adapter. Services ask this interface for a profile, so the synthetic Mock and a
# future account-aggregator adapter are interchangeable and tests need no network.
class FinancialProfilePort(ABC):
    """Gives the monthly inflow and existing EMIs for one customer session, in domain terms.

    Called only after the customer consents to the comfort check (CLAUDE.md section 2, rule 9).
    """

    @abstractmethod
    def get_financial_profile(self, customer_session_id: str) -> FinancialProfile:
        """Gives the financial profile behind the customer session."""
