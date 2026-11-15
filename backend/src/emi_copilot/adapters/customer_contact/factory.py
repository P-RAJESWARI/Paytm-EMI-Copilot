"""CustomerContactFactory: the one place that chooses where the customer's phone number comes from.

Only the composition root (api/dependencies.py) imports this module (ADR 0008).
"""

from emi_copilot.adapters.customer_contact.mock_adapter import MockPaytmCustomerContactAdapter
from emi_copilot.adapters.customer_contact.port import CustomerContactPort
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode

PAYTM_MODE_WITHOUT_CUSTOMER_CONTACT_SOURCE_MESSAGE = (
    "PAYMENT_GATEWAY_MODE=paytm has no real customer phone number source yet: only "
    "MockPaytmCustomerContactAdapter exists, which gives every customer one synthetic number. "
    "Refusing to start until Paytm confirms a source [Verify with Paytm] (ADR 0004, ADR 0022)."
)


class CustomerContactConfigurationError(ValueError):
    """Raised at startup when the gateway mode needs a phone number source that does not exist."""


# Pattern: Factory. Only the labelled Mock exists until Paytm confirms a source (ADR 0022
# decision 2); a real adapter would be chosen here. Like the gateway (ADR 0004), paytm mode never
# falls back to the Mock: startup fails instead.
class CustomerContactFactory:
    """Builds the CustomerContactPort the application uses."""

    def __init__(self, settings: ApplicationSettings) -> None:
        """Keeps the settings that hold the gateway mode."""
        self._settings = settings

    def create(self) -> CustomerContactPort:
        """Builds the Mock contact adapter, which announces itself; refuses paytm mode."""
        if self._settings.payment_gateway_mode is PaymentGatewayMode.PAYTM:
            raise CustomerContactConfigurationError(
                PAYTM_MODE_WITHOUT_CUSTOMER_CONTACT_SOURCE_MESSAGE
            )
        return MockPaytmCustomerContactAdapter()
