"""MockSyntheticFinancialProfileAdapter: labelled, synthetic design profiles per session."""

import logging

import pytest

from emi_copilot.adapters.financial_profile.mock_adapter import (
    MOCK_ACTIVE_WARNING,
    RISKY_SYNTHETIC_PROFILE,
    STANDARD_SYNTHETIC_PROFILE,
    MockSyntheticFinancialProfileAdapter,
)
from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.domain.money import Money

RISKY_SESSION_ID = "customer-session-sample-risky"
STANDARD_SESSION_ID = "customer-session-sample-4821"


def test_mock_adapter_is_a_labelled_financial_profile_port() -> None:
    """The Mock implements the port and says "Mock" in its class name (CLAUDE.md rule 10)."""
    mock_adapter = MockSyntheticFinancialProfileAdapter()
    assert isinstance(mock_adapter, FinancialProfilePort)
    assert "Mock" in type(mock_adapter).__name__


def test_mock_adapter_construction_announces_synthetic_profiles_as_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Building the Mock logs a WARNING, so nobody can believe real account data is read."""
    with caplog.at_level(logging.WARNING):
        MockSyntheticFinancialProfileAdapter()
    assert [record.getMessage() for record in caplog.records] == [MOCK_ACTIVE_WARNING]


def test_mock_adapter_by_default_gives_every_session_the_standard_profile() -> None:
    """Without listed sessions every customer is the design's ₹30,000 / ₹8,000 customer."""
    profile = MockSyntheticFinancialProfileAdapter().get_financial_profile(RISKY_SESSION_ID)
    assert profile == STANDARD_SYNTHETIC_PROFILE
    assert profile.monthly_inflow == Money.from_rupees("30000")
    assert profile.existing_emis_per_month == Money.from_rupees("8000")


def test_mock_adapter_gives_listed_sessions_the_risky_profile() -> None:
    """A listed session is the design's ₹20,000 / ₹8,000 customer; others stay standard."""
    mock_adapter = MockSyntheticFinancialProfileAdapter(
        risky_customer_session_ids=frozenset({RISKY_SESSION_ID})
    )
    risky_profile = mock_adapter.get_financial_profile(RISKY_SESSION_ID)
    assert risky_profile == RISKY_SYNTHETIC_PROFILE
    assert risky_profile.monthly_inflow == Money.from_rupees("20000")
    assert risky_profile.existing_emis_per_month == Money.from_rupees("8000")
    assert mock_adapter.get_financial_profile(STANDARD_SESSION_ID) == STANDARD_SYNTHETIC_PROFILE
