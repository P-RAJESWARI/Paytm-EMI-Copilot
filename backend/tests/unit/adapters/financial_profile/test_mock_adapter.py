"""MockSyntheticFinancialProfileAdapter: one labelled synthetic design profile for all sessions."""

import logging

import pytest

from emi_copilot.adapters.financial_profile.mock_adapter import (
    MOCK_ACTIVE_WARNING_TEMPLATE,
    RISKY_SYNTHETIC_PROFILE,
    STANDARD_SYNTHETIC_PROFILE,
    MockSyntheticFinancialProfileAdapter,
)
from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.config.settings import MockFinancialProfileChoice
from emi_copilot.domain.money import Money

FIRST_SESSION_ID = "customer-session-sample-4821"
SECOND_SESSION_ID = "customer-session-sample-4822"


def test_mock_adapter_is_a_labelled_financial_profile_port() -> None:
    """The Mock implements the port and says "Mock" in its class name (CLAUDE.md rule 10)."""
    mock_adapter = MockSyntheticFinancialProfileAdapter()
    assert isinstance(mock_adapter, FinancialProfilePort)
    assert "Mock" in type(mock_adapter).__name__


@pytest.mark.parametrize("profile_choice", list(MockFinancialProfileChoice))
def test_mock_adapter_construction_announces_the_chosen_synthetic_profile_as_a_warning(
    caplog: pytest.LogCaptureFixture, profile_choice: MockFinancialProfileChoice
) -> None:
    """Building the Mock logs a WARNING naming the profile, so nobody mistakes it for real data."""
    with caplog.at_level(logging.WARNING):
        MockSyntheticFinancialProfileAdapter(profile_choice)
    assert [record.getMessage() for record in caplog.records] == [
        MOCK_ACTIVE_WARNING_TEMPLATE % profile_choice.value
    ]
    assert f"synthetic {profile_choice.value} profile" in caplog.text


def test_mock_adapter_by_default_gives_every_session_the_standard_profile() -> None:
    """By default every customer is the design's ₹30,000 / ₹8,000 customer."""
    mock_adapter = MockSyntheticFinancialProfileAdapter()
    profile = mock_adapter.get_financial_profile(FIRST_SESSION_ID)
    assert profile == STANDARD_SYNTHETIC_PROFILE
    assert profile.monthly_inflow == Money.from_rupees("30000")
    assert profile.existing_emis_per_month == Money.from_rupees("8000")
    assert mock_adapter.get_financial_profile(SECOND_SESSION_ID) == STANDARD_SYNTHETIC_PROFILE


def test_mock_adapter_with_the_risky_choice_gives_every_session_the_risky_profile() -> None:
    """MOCK_FINANCIAL_PROFILE=risky makes every customer the design's ₹20,000 / ₹8,000 one."""
    mock_adapter = MockSyntheticFinancialProfileAdapter(MockFinancialProfileChoice.RISKY)
    risky_profile = mock_adapter.get_financial_profile(FIRST_SESSION_ID)
    assert risky_profile == RISKY_SYNTHETIC_PROFILE
    assert risky_profile.monthly_inflow == Money.from_rupees("20000")
    assert risky_profile.existing_emis_per_month == Money.from_rupees("8000")
    assert mock_adapter.get_financial_profile(SECOND_SESSION_ID) == RISKY_SYNTHETIC_PROFILE
