"""MarkSaleReadyToPayService: records the plan a customer agreed to and moves the sale on."""

from dataclasses import dataclass

from emi_copilot.core.clock import Clock
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.errors import (
    IllegalSaleTransitionError,
    OfferNotFoundError,
    ProductNotFoundError,
    SaleNotFoundError,
)
from emi_copilot.domain.payments import OfferDiscoveryQuery
from emi_copilot.domain.sales import ChosenPlan, Sale
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.sale_expiry import SaleExpiryStep, build_sale_status_changed


@dataclass(frozen=True, slots=True)
class MarkSaleReadyToPayCommand:
    """The customer agreed to one offer for one sale; every figure is re-quoted server-side."""

    sale_id: str
    offer_id: str


def _require_sale(sale: Sale | None) -> Sale:
    """Returns the sale, or raises when no sale has the id."""
    if sale is None:
        raise SaleNotFoundError("No sale has this id.")
    return sale


class MarkSaleReadyToPayService:
    """Re-quotes the agreed offer, freezes it as the ChosenPlan and moves CHOOSING to READY_TO_PAY.

    Callers: Layer 3 consent and the step 2.3 Mock customer simulator; no merchant endpoint
    calls it, because agreeing is the customer's step (rule 9). The quote is fetched outside any
    transaction; the move then runs on the locked sale, expiring it first if overdue, and a
    refusal is raised after that expiry commits.
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        offer_discovery_service: OfferDiscoveryService,
        clock: Clock,
        event_bus: DomainEventBus,
        sale_expiry: SaleExpiryStep,
    ) -> None:
        """Keeps the collaborators of the move."""
        self._unit_of_work_factory = unit_of_work_factory
        self._offer_discovery_service = offer_discovery_service
        self._clock = clock
        self._event_bus = event_bus
        self._sale_expiry = sale_expiry

    def mark_ready_to_pay(self, command: MarkSaleReadyToPayCommand) -> Sale:
        """Gives the READY_TO_PAY sale; raises not found, OfferNotFoundError or a state conflict."""
        with self._unit_of_work_factory() as unit_of_work:
            sale = _require_sale(unit_of_work.sales.find_by_id_for_update(command.sale_id))
            product = self._require_product(unit_of_work, sale)
        chosen_plan = self._quote_chosen_plan(sale, product, command.offer_id)
        refusal: IllegalSaleTransitionError | None = None
        with self._unit_of_work_factory() as unit_of_work:
            locked_sale = _require_sale(unit_of_work.sales.find_by_id_for_update(command.sale_id))
            now = self._clock.now()
            current_sale = self._sale_expiry.expire_if_overdue(unit_of_work, locked_sale, now)
            try:
                agreed_sale = current_sale.agree_to_plan(chosen_plan, now)
            except IllegalSaleTransitionError as transition_refusal:
                refusal = transition_refusal
            else:
                unit_of_work.sales.update(agreed_sale)
                self._event_bus.publish(
                    build_sale_status_changed(current_sale, agreed_sale), unit_of_work
                )
        if refusal is not None:
            raise refusal
        return agreed_sale

    def _require_product(self, unit_of_work: UnitOfWork, sale: Sale) -> CatalogueProduct:
        """Gives the sale's product from its shop's catalogue."""
        product = unit_of_work.products.find_by_id_for_merchant(sale.merchant_id, sale.product_id)
        if product is None:
            raise ProductNotFoundError("The product of a stored sale is not in the catalogue.")
        return product

    def _quote_chosen_plan(
        self, sale: Sale, product: CatalogueProduct, offer_id: str
    ) -> ChosenPlan:
        """Re-discovers the offers at the sale's price and freezes the agreed one as shown."""
        priced_offers = self._offer_discovery_service.discover_offers(
            OfferDiscoveryQuery(
                price=sale.price,
                product_id=product.gateway_product_id,
                brand_id=product.gateway_brand_id,
                category_id=product.gateway_category_id,
            )
        )
        agreed_offer = next(
            (offer for offer in priced_offers if offer.offer.offer_id == offer_id), None
        )
        if agreed_offer is None:
            raise OfferNotFoundError("The agreed offer is not quoted for this sale's item.")
        return ChosenPlan.from_priced_offer(agreed_offer)
