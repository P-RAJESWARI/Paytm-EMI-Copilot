"""The test-side view of one gateway implementation, so one contract suite runs against each."""

from abc import ABC, abstractmethod

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import GatewayPaymentStatus, UnverifiedWebhookNotification


# Pattern: Adapter (test side). Hides how each implementation is driven (a clock for the Mock,
# scripted fixture responses for a real adapter) behind the few moves the contract suite needs.
class GatewayContractHarness(ABC):
    """One gateway under contract test, plus the levers that make it reach each tested state."""

    @property
    @abstractmethod
    def gateway(self) -> PaymentGatewayPort:
        """Gives the gateway implementation under test, fresh for every test."""

    @abstractmethod
    def make_order_paid(self, order_id: str) -> None:
        """Brings the gateway to report a linked order as paid at the link's amount."""

    @abstractmethod
    def make_valid_notification(
        self,
        order_id: str,
        status: GatewayPaymentStatus,
        transaction_id: str | None,
        amount: Money | None,
    ) -> UnverifiedWebhookNotification:
        """Builds a notification, in the gateway's own format, that carries a genuine signature."""

    @abstractmethod
    def make_tampered_notification(
        self,
        order_id: str,
        status: GatewayPaymentStatus,
        transaction_id: str | None,
        amount: Money | None,
    ) -> UnverifiedWebhookNotification:
        """Builds a genuinely signed notification and then changes one field after signing."""
