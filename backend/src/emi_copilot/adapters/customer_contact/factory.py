"""CustomerContactFactory: the one place that chooses where the customer's phone number comes from.

Only the composition root (api/dependencies.py) imports this module (ADR 0008).
"""

from emi_copilot.adapters.customer_contact.mock_adapter import MockPaytmCustomerContactAdapter
from emi_copilot.adapters.customer_contact.port import CustomerContactPort


# Pattern: Factory. Only the labelled Mock exists until Paytm confirms a source (ADR 0022
# decision 2), so there is no mode setting yet; a real adapter would be chosen here.
class CustomerContactFactory:
    """Builds the CustomerContactPort the application uses."""

    def create(self) -> CustomerContactPort:
        """Builds the Mock contact adapter, which announces itself in the startup log."""
        return MockPaytmCustomerContactAdapter()
