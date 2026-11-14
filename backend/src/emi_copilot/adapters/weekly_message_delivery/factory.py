"""WeeklyMessageDeliveryFactory: the one place that chooses the weekly message channel.

Only the composition root (api/dependencies.py) imports this module (ADR 0008).
"""

from emi_copilot.adapters.weekly_message_delivery.mock_adapter import (
    MockWeeklyMessageDeliveryAdapter,
)
from emi_copilot.adapters.weekly_message_delivery.port import WeeklyMessageDeliveryPort


# Pattern: Factory. "Sent" is simulated for the demo (plan Q14), so only the Mock exists and
# there is no mode setting yet; a real channel would be chosen here.
class WeeklyMessageDeliveryFactory:
    """Builds the WeeklyMessageDeliveryPort the application uses."""

    def create(self) -> WeeklyMessageDeliveryPort:
        """Builds the Mock delivery adapter, which announces itself in the startup log."""
        return MockWeeklyMessageDeliveryAdapter()
