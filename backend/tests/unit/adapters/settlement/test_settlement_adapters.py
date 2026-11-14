"""The settlement Mock announces itself (rule 10) and the factory builds it."""

import logging

import pytest

from emi_copilot.adapters.settlement.factory import SettlementFactory
from emi_copilot.adapters.settlement.mock_adapter import (
    MOCK_SETTLEMENT_ACTIVE_WARNING,
    MockSettlementAdapter,
)


def test_settlement_factory_builds_the_mock_and_it_warns_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The only implementation is the labelled Mock, announced in the startup log."""
    with caplog.at_level(logging.WARNING):
        adapter = SettlementFactory().create()
    assert isinstance(adapter, MockSettlementAdapter)
    assert adapter.adapter_name == "mock"
    assert [record.getMessage() for record in caplog.records] == [MOCK_SETTLEMENT_ACTIVE_WARNING]
    assert "Mock" in type(adapter).__name__
