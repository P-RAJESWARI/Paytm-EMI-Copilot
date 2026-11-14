"""Contract harness for PaytmPaymentGatewayAdapter, fed by documented-shape fixtures [Verify]."""

from decimal import Decimal
from typing import override

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import GatewayPaymentStatus, UnverifiedWebhookNotification
from tests.contract.payment_gateway.gateway_contract_harness import GatewayContractHarness
from tests.contract.payment_gateway.paytm_adapter_builder import build_paytm_adapter_under_test

# How the fake writes each of our statuses in Paytm's webhook vocabulary [Verify].
WEBHOOK_STATUS_VALUES = {
    GatewayPaymentStatus.PAID: "TXN_SUCCESS",
    GatewayPaymentStatus.FAILED: "TXN_FAILURE",
    GatewayPaymentStatus.PENDING: "PENDING",
}
ONE_PAISA = Decimal("0.01")


class PaytmGatewayContractHarness(GatewayContractHarness):
    """Drives the real Paytm adapter against a fake Paytm on httpx.MockTransport."""

    def __init__(self) -> None:
        """Builds the adapter on a fresh fake server with the synthetic merchant id and key."""
        self._adapter_under_test = build_paytm_adapter_under_test()

    @property
    @override
    def gateway(self) -> PaymentGatewayPort:
        """Gives the Paytm adapter under test."""
        return self._adapter_under_test.adapter

    @override
    def make_order_paid(self, order_id: str) -> None:
        """Makes the fake's status API report the order paid at its link amount."""
        self._adapter_under_test.server.mark_order_paid(order_id)

    @override
    def make_valid_notification(
        self,
        order_id: str,
        status: GatewayPaymentStatus,
        transaction_id: str | None,
        amount: Money | None,
    ) -> UnverifiedWebhookNotification:
        """Builds Paytm's webhook fields for the event and signs them with the official library."""
        signed_fields = self._adapter_under_test.server.build_signed_webhook_fields(
            order_id,
            WEBHOOK_STATUS_VALUES[status],
            transaction_id or "",
            None if amount is None else f"{amount.amount_in_rupees:.2f}",
        )
        return UnverifiedWebhookNotification(received_fields=signed_fields)

    @override
    def make_tampered_notification(
        self,
        order_id: str,
        status: GatewayPaymentStatus,
        transaction_id: str | None,
        amount: Money | None,
    ) -> UnverifiedWebhookNotification:
        """Signs the fields, then raises TXNAMOUNT by one paisa after signing."""
        signed_notification = self.make_valid_notification(order_id, status, transaction_id, amount)
        tampered_fields = dict(signed_notification.received_fields)
        tampered_amount = Decimal(tampered_fields["TXNAMOUNT"]) + ONE_PAISA
        tampered_fields["TXNAMOUNT"] = f"{tampered_amount:.2f}"
        return UnverifiedWebhookNotification(received_fields=tampered_fields)
