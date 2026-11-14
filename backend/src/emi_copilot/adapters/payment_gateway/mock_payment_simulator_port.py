"""MockPaymentSimulatorPort: the customer's side of a Mock payment, for the labelled simulator.

Only MockCustomerSimulator uses it (CLAUDE.md rules 9 and 10). A real gateway has no such
control: there the customer pays on the gateway's own page and the gateway reports it.
"""

from abc import ABC, abstractmethod

from emi_copilot.domain.payments import UnverifiedWebhookNotification


# Pattern: Port and Adapter. Services may not import the concrete Mock (ADR 0008), so the Mock's
# "the customer paid" control is reached through this port; only the Mock implements it.
class MockPaymentSimulatorPort(ABC):
    """Plays the customer paying a Mock payment link, as a demo stand-in for a real customer."""

    @abstractmethod
    def complete_mock_payment(self, order_id: str) -> UnverifiedWebhookNotification:
        """Marks the Mock order paid and gives the signed PAID notification the Mock would send.

        The notification is not trusted by being returned here: it still goes through webhook
        verification, so the payment reaches PAID only by the normal server-side path.

        Raises:
            InvalidPaymentGatewayValueError: the Mock holds no payment link for this order id.
        """
