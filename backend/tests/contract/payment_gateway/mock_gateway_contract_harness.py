"""Contract harness for MockPaymentGatewayAdapter: a fixed clock moves its payments along."""

from typing import override

from emi_copilot.adapters.payment_gateway.mock_adapter import (
    DEFAULT_PAYMENT_COMPLETION_DELAY,
    MockPaymentGatewayAdapter,
)
from emi_copilot.adapters.payment_gateway.mock_webhook_signature import MOCK_AMOUNT_IN_PAISE_FIELD
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import GatewayPaymentStatus, UnverifiedWebhookNotification
from tests.contract.payment_gateway.gateway_contract_harness import GatewayContractHarness
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT

# Synthetic and low-entropy on purpose: a test signing key, never a real secret.
SYNTHETIC_WEBHOOK_SIGNING_SECRET = bytes(range(32))


class MockGatewayContractHarness(GatewayContractHarness):
    """Drives a fresh Mock adapter whose clock only moves when the harness moves it."""

    def __init__(self) -> None:
        """Builds the Mock with a synthetic secret, a fixed clock and the default delay."""
        self._clock = FixedClock(CREATED_AT)
        self._mock_gateway = MockPaymentGatewayAdapter(
            clock=self._clock, webhook_signing_secret=SYNTHETIC_WEBHOOK_SIGNING_SECRET
        )

    @property
    @override
    def gateway(self) -> PaymentGatewayPort:
        """Gives the Mock adapter under test."""
        return self._mock_gateway

    @override
    def make_order_paid(self, order_id: str) -> None:
        """Lets the Mock's completion delay pass, after which every linked order is paid."""
        self._clock.advance(DEFAULT_PAYMENT_COMPLETION_DELAY)

    @override
    def make_valid_notification(
        self,
        order_id: str,
        status: GatewayPaymentStatus,
        transaction_id: str | None,
        amount: Money | None,
    ) -> UnverifiedWebhookNotification:
        """Signs the notification with the Mock's own helper and secret."""
        return self._mock_gateway.build_signed_notification(
            order_id, status, transaction_id, amount
        )

    @override
    def make_tampered_notification(
        self,
        order_id: str,
        status: GatewayPaymentStatus,
        transaction_id: str | None,
        amount: Money | None,
    ) -> UnverifiedWebhookNotification:
        """Signs the notification, then raises the amount by one paisa after signing."""
        signed_notification = self.make_valid_notification(order_id, status, transaction_id, amount)
        tampered_fields = dict(signed_notification.received_fields)
        signed_amount_in_paise = int(tampered_fields[MOCK_AMOUNT_IN_PAISE_FIELD] or "0")
        tampered_fields[MOCK_AMOUNT_IN_PAISE_FIELD] = str(signed_amount_in_paise + 1)
        return UnverifiedWebhookNotification(received_fields=tampered_fields)
