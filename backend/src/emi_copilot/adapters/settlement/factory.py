"""SettlementFactory: the one place that chooses the settlement adapter.

Only the composition root (api/dependencies.py) imports this module (ADR 0008).
"""

from emi_copilot.adapters.settlement.mock_adapter import MockSettlementAdapter
from emi_copilot.adapters.settlement.port import SettlementPort


# Pattern: Factory. Only the labelled Mock exists until a real settlement source is decided
# (ADR 0006), so there is no mode setting yet; a real adapter would be chosen here.
class SettlementFactory:
    """Builds the SettlementPort the application uses."""

    def create(self) -> SettlementPort:
        """Builds the Mock settlement adapter, which announces itself in the startup log."""
        return MockSettlementAdapter()
