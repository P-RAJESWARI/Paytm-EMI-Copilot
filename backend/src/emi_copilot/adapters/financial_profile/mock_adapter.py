"""MockSyntheticFinancialProfileAdapter: labelled synthetic profiles; no account data is read."""

import logging

from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.money import Money

MOCK_ACTIVE_WARNING = (
    "MockSyntheticFinancialProfileAdapter active: comfort checks use synthetic profiles"
)
STANDARD_SYNTHETIC_PROFILE = FinancialProfile(
    monthly_inflow=Money.from_rupees(30000), existing_emis_per_month=Money.from_rupees(8000)
)
"""The design's customer: inflow ₹30,000, existing EMIs ₹8,000 (26.67%; ADR 0020 decision 6)."""

RISKY_SYNTHETIC_PROFILE = FinancialProfile(
    monthly_inflow=Money.from_rupees(20000), existing_emis_per_month=Money.from_rupees(8000)
)
"""The design's second customer: inflow ₹20,000, existing EMIs ₹8,000; plan B gives 59.25%."""

mock_financial_profile_logger = logging.getLogger(__name__)


# Pattern: Adapter (Mock). Implements FinancialProfilePort with synthetic data, so the comfort check
# can be demonstrated without any account-aggregator integration (CLAUDE.md section 2, rule 10).
class MockSyntheticFinancialProfileAdapter(FinancialProfilePort):
    """Gives the risky synthetic profile to listed sessions and the standard one to all others."""

    def __init__(self, risky_customer_session_ids: frozenset[str] = frozenset()) -> None:
        """Stores the sessions that get the risky profile and announces that this is a Mock."""
        self._risky_customer_session_ids = frozenset(risky_customer_session_ids)
        mock_financial_profile_logger.warning(
            MOCK_ACTIVE_WARNING, extra={"financial_profile_adapter": "mock"}
        )

    def get_financial_profile(self, customer_session_id: str) -> FinancialProfile:
        """Gives the risky profile for a listed session id, else the standard profile."""
        if customer_session_id in self._risky_customer_session_ids:
            return RISKY_SYNTHETIC_PROFILE
        return STANDARD_SYNTHETIC_PROFILE
