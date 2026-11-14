"""SaleHandoffService: M4's hand-off of an agreed sale to the payment gateway, and its status."""

from emi_copilot.core.clock import Clock
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.errors import IllegalSaleTransitionError, ProductNotFoundError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.domain.payments import PaymentAttempt
from emi_copilot.domain.sales import Sale, SaleStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory
from emi_copilot.services.payment_handoff_service import PaymentHandoffService
from emi_copilot.services.payment_handoff_types import CreatePaymentLinkCommand, PaymentLinkHandoff
from emi_copilot.services.payment_status_service import PaymentStatusService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.sale_handoff_views import (
    SaleHandoffView,
    build_sale_handoff_view,
    require_agreed_plan,
)
from emi_copilot.services.sale_payment_link_intent import SalePaymentLinkIntent
from emi_copilot.services.sale_views import CounterSale, build_counter_sale

STATUSES_ACCEPTING_A_NEW_LINK = frozenset(
    {SaleStatus.READY_TO_PAY, SaleStatus.PAYMENT_NOT_COMPLETED}
)
"""A link is made only while the customer's agreed payment is still due."""


def _require_product(unit_of_work: UnitOfWork, sale: Sale) -> CatalogueProduct:
    """Gives the sale's product from its own shop's catalogue."""
    product = unit_of_work.products.find_by_id_for_merchant(sale.merchant_id, sale.product_id)
    if product is None:
        raise ProductNotFoundError("The product of a stored sale is not in the shop's catalogue.")
    return product


class SaleHandoffService:
    """Hands an agreed sale's plan to the gateway as a link and reports the payment, per shop.

    Every idempotency, gateway and outcome rule is PaymentHandoffService's and every status
    rule PaymentStatusService's; this class adds only the sale's rules (SalePaymentLinkIntent)
    and the merchant scope: another shop's sale is not found (404). There is no way to mark a
    sale paid here (plan Q5): PAID comes only from a verified gateway report.
    """

    def __init__(  # noqa: PLR0913 - one parameter per collaborator
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        event_bus: DomainEventBus,
        sale_expiry: SaleExpiryStep,
        payment_handoff_service: PaymentHandoffService,
        payment_status_service: PaymentStatusService,
    ) -> None:
        """Keeps the collaborators; the two payment services do all of the gateway work."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._event_bus = event_bus
        self._sale_expiry = sale_expiry
        self._payment_handoff_service = payment_handoff_service
        self._payment_status_service = payment_status_service

    def get_handoff(self, principal: MerchantPrincipal, sale_id: str) -> SaleHandoffView:
        """Gives M4's view of the shop's agreed sale; CHOOSING or EXPIRED is SALE_STATE_CONFLICT."""
        counter_sale, latest_attempt = self._read_sale_and_latest_attempt(principal, sale_id)
        return build_sale_handoff_view(counter_sale, latest_attempt)

    def create_payment_link(
        self, principal: MerchantPrincipal, sale_id: str, idempotency_key: str
    ) -> PaymentLinkHandoff:
        """Makes a link for the agreed plan once per key; a known key replays in any status."""
        with self._unit_of_work_factory() as unit_of_work:
            sale = self._sale_expiry.load_current_sale_for_update(
                unit_of_work, principal.merchant_id, sale_id, self._clock.now()
            )
            product = _require_product(unit_of_work, sale)
        chosen_plan = require_agreed_plan(sale)
        command = CreatePaymentLinkCommand(
            idempotency_key=idempotency_key,
            offer_id=chosen_plan.offer_id,
            price=sale.price,
            product_id=product.gateway_product_id,
            brand_id=product.gateway_brand_id,
            category_id=product.gateway_category_id,
            sale_id=sale.id,
        )
        if sale.status not in STATUSES_ACCEPTING_A_NEW_LINK:
            replayed_handoff = self._payment_handoff_service.replay_if_known(command)
            if replayed_handoff is not None:
                return replayed_handoff
            raise IllegalSaleTransitionError(
                f"A sale that is {sale.status.value} takes no new payment link."
            )
        intent = SalePaymentLinkIntent(sale, chosen_plan, self._clock, self._event_bus)
        return self._payment_handoff_service.create_payment_link(command, intent)

    def check_payment_status(self, principal: MerchantPrincipal, sale_id: str) -> SaleHandoffView:
        """Confirms the latest attempt's payment with the gateway, applies it, gives the view.

        A PAID sale is final, so the gateway is not asked again; a sale with no attempt yet
        has nothing to ask about.
        """
        counter_sale, latest_attempt = self._read_sale_and_latest_attempt(principal, sale_id)
        if counter_sale.sale.status is not SaleStatus.PAID and latest_attempt is not None:
            self._payment_status_service.get_payment_status(latest_attempt.order_id)
        return self.get_handoff(principal, sale_id)

    def _read_sale_and_latest_attempt(
        self, principal: MerchantPrincipal, sale_id: str
    ) -> tuple[CounterSale, PaymentAttempt | None]:
        """Reads the shop's sale (expired first if overdue), its product name and newest attempt.

        The expiry commits before an agreed plan is required, so a refusal never undoes it.
        """
        with self._unit_of_work_factory() as unit_of_work:
            sale = self._sale_expiry.load_current_sale_for_update(
                unit_of_work, principal.merchant_id, sale_id, self._clock.now()
            )
            counter_sale = build_counter_sale(unit_of_work, sale)
            latest_attempt = unit_of_work.payment_attempts.find_latest_for_sale(sale.id)
        require_agreed_plan(sale)
        return counter_sale, latest_attempt
