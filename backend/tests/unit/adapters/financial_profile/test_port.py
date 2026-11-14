"""Tests that pin FinancialProfilePort: domain terms only, and no use without an adapter."""

from pathlib import Path

import pytest

from emi_copilot.adapters.financial_profile import port
from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from tests.unit.architecture.test_import_boundaries import find_disallowed_imports


def test_financial_profile_port_declares_only_get_financial_profile() -> None:
    """The port offers one read in our words and nothing else."""
    assert FinancialProfilePort.__abstractmethods__ == frozenset({"get_financial_profile"})


def test_financial_profile_port_cannot_be_instantiated_without_an_adapter() -> None:
    """Only a concrete adapter can serve as the profile source."""
    with pytest.raises(TypeError, match="abstract"):
        FinancialProfilePort()  # type: ignore[abstract]


def test_financial_profile_port_imports_only_standard_library_and_domain() -> None:
    """The port is expressed in domain terms, so it cannot depend on any vendor or library."""
    assert find_disallowed_imports(Path(port.__file__)) == []
