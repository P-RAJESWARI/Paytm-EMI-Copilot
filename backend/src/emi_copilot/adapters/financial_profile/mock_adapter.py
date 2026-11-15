"""MockSyntheticFinancialProfileAdapter: labelled synthetic profiles; no account data is read."""

import logging

from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.config.settings import MockFinancialProfileChoice
from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.money import Money

MOCK_ACTIVE_WARNING_TEMPLATE = (
    "MockSyntheticFinancialProfileAdapter active: every comfort check uses the synthetic "
    "%s profile (MOCK_FINANCIAL_PROFILE)"
)
STANDARD_SYNTHETIC_PROFILE = FinancialProfile(
    monthly_inflow=Money.from_rupees(30000), existing_emis_per_month=Money.from_rupees(8000)
)
"""The design's customer: inflow ₹30,000, existing EMIs ₹8,000 (26.67%; ADR 0020 decision 6)."""

RISKY_SYNTHETIC_PROFILE = FinancialProfile(
    monthly_inflow=Money.from_rupees(20000), existing_emis_per_month=Money.from_rupees(8000)
)
"""The design's second customer: inflow ₹20,000, existing EMIs ₹8,000; plan B gives 59.25%."""

SYNTHETIC_PROFILES_BY_CHOICE = {
    MockFinancialProfileChoice.STANDARD: STANDARD_SYNTHETIC_PROFILE,
    MockFinancialProfileChoice.RISKY: RISKY_SYNTHETIC_PROFILE,
}

mock_financial_profile_logger = logging.getLogger(__name__)


# Pattern: Adapter (Mock). Implements FinancialProfilePort with synthetic data, so the comfort check
# can be demonstrated without any account-aggregator integration (CLAUDE.md section 2, rule 10).
class MockSyntheticFinancialProfileAdapter(FinancialProfilePort):
    """Gives every customer session the one synthetic profile chosen by MOCK_FINANCIAL_PROFILE."""

    def __init__(
        self, profile_choice: MockFinancialProfileChoice = MockFinancialProfileChoice.STANDARD
    ) -> None:
        """Keeps the chosen profile and announces, naming it, that profiles are synthetic."""
        self._profile = SYNTHETIC_PROFILES_BY_CHOICE[profile_choice]
        mock_financial_profile_logger.warning(
            MOCK_ACTIVE_WARNING_TEMPLATE,
            profile_choice.value,
            extra={"financial_profile_adapter": "mock"},
        )

    def get_financial_profile(self, customer_session_id: str) -> FinancialProfile:  # noqa: ARG002 - one profile for all
        """Gives the chosen synthetic profile, whichever session asks."""
        return self._profile
