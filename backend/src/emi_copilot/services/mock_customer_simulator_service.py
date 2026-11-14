"""MockCustomerSimulatorService: plays the customer's steps in the demo until Layer 3 exists.

Labelled Mock (CLAUDE.md rule 10) and enabled only by MOCK_CUSTOMER_SIMULATOR_ENABLED, never in
paytm mode. It takes no shortcut: agreeing goes through MarkSaleReadyToPayService, the very
service Layer 3 consent will call, and paying makes the Mock gateway pay, then hands the Mock's
signed notification to the webhook path, which verifies it before anything changes. Nothing
here sets a sale's status.
"""

from emi_copilot.adapters.payment_gateway.mock_payment_simulator_port import (
    MockPaymentSimulatorPort,
)
from emi_copilot.domain.errors import PaymentAttemptNotFoundError, SaleNotFoundError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.mark_sale_ready_to_pay_service import (
    MarkSaleReadyToPayCommand,
    MarkSaleReadyToPayService,
)
from emi_copilot.services.merchant_payment_scope import find_merchant_payment_attempt
from emi_copilot.services.payment_status_service import PaymentStatusService, WebhookApplication
from emi_copilot.services.sale_expiry import SALE_NOT_FOUND_DETAIL
from emi_copilot.services.sale_views import CounterSale, build_counter_sale


class MockCustomerSimulatorService:
    """Agrees a plan and pays a Mock link in the customer's place, for the shop's own sales only.

    The signed-in shop drives it from the demo (rule 9 still holds for real customers: Layer 3
    replaces it). Another shop's sale or payment is not found (404).
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        mark_sale_ready_to_pay_service: MarkSaleReadyToPayService,
        payment_status_service: PaymentStatusService,
        mock_payment_simulator: MockPaymentSimulatorPort,
    ) -> None:
        """Keeps the services the real flow uses and the Mock gateway's customer controls."""
        self._unit_of_work_factory = unit_of_work_factory
        self._mark_sale_ready_to_pay_service = mark_sale_ready_to_pay_service
        self._payment_status_service = payment_status_service
        self._mock_payment_simulator = mock_payment_simulator

    def agree_to_plan(
        self, principal: MerchantPrincipal, sale_id: str, offer_id: str
    ) -> CounterSale:
        """Agrees the offer on the shop's sale as the customer would; gives the sale after it."""
        with self._unit_of_work_factory() as unit_of_work:
            if unit_of_work.sales.find_by_id_for_merchant(principal.merchant_id, sale_id) is None:
                raise SaleNotFoundError(SALE_NOT_FOUND_DETAIL)
        agreed_sale = self._mark_sale_ready_to_pay_service.mark_ready_to_pay(
            MarkSaleReadyToPayCommand(sale_id=sale_id, offer_id=offer_id)
        )
        with self._unit_of_work_factory() as unit_of_work:
            return build_counter_sale(unit_of_work, agreed_sale)

    def complete_payment(self, principal: MerchantPrincipal, order_id: str) -> WebhookApplication:
        """Pays the shop's Mock link as the customer would; the signed report then moves it."""
        with self._unit_of_work_factory() as unit_of_work:
            shops_attempt = find_merchant_payment_attempt(
                unit_of_work, principal.merchant_id, order_id
            )
        if shops_attempt is None:
            raise PaymentAttemptNotFoundError(f"No payment of this shop has order id {order_id}.")
        notification = self._mock_payment_simulator.complete_mock_payment(order_id)
        return self._payment_status_service.apply_webhook(notification)
