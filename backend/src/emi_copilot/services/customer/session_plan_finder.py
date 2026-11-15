"""SessionPlanFinder: one of the session's plans, re-quoted now for its item at the sale price."""

from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import OfferNotFoundError
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.customer.customer_session_access import (
    CustomerSessionAccess,
    build_sale_offer_query,
    find_sale_product,
)
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.plan_advice_types import PricedOfferSource
from emi_copilot.services.sale_expiry import SaleExpiryStep


class SessionPlanFinder:
    """Checks the session token and gives the offer's figures as quoted now for its item."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        sale_expiry: SaleExpiryStep,
        offer_source: PricedOfferSource,
    ) -> None:
        """Keeps the session check and the offer source."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._session_access = CustomerSessionAccess(sale_expiry)
        self._offer_source = offer_source

    def find_plan(self, credentials: CustomerSessionCredentials, offer_id: str) -> ChosenPlan:
        """Gives the offer's plan for the session's item and price.

        Raises OfferNotFoundError when the offer is not quoted for that item and price.
        """
        with self._unit_of_work_factory() as unit_of_work:
            opened = self._session_access.open_sale(unit_of_work, credentials, self._clock.now())
            item = build_sale_offer_query(opened.sale, find_sale_product(unit_of_work, opened.sale))
        for priced_offer in self._offer_source.discover_offers(item):
            if priced_offer.offer.offer_id == offer_id:
                return ChosenPlan.from_priced_offer(priced_offer)
        raise OfferNotFoundError("The offer is not quoted for this item and price.")
