"""CustomerExplanationService: explains one of the session's plans with fresh figures (C7)."""

from emi_copilot.core.clock import Clock
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import OfferNotFoundError
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.customer.customer_session_access import (
    CustomerSessionAccess,
    build_sale_offer_query,
    find_sale_product,
)
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.customer.explanation_types import ExplanationText, PlanExplainer
from emi_copilot.services.plan_advice_types import PricedOfferSource
from emi_copilot.services.sale_expiry import SaleExpiryStep


class CustomerExplanationService:
    """Re-quotes the chosen offer on the session's item and hands its figures to the explainer.

    The explainer is the TemplateExplanationService today; Layer 4 passes an audited AI explainer
    behind the same PlanExplainer interface. The explainer only words the figures; it never
    computes or changes them (CLAUDE.md section 2, rules 1 and 2).
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        sale_expiry: SaleExpiryStep,
        offer_source: PricedOfferSource,
        plan_explainer: PlanExplainer,
    ) -> None:
        """Keeps the session check, the offer source and the explainer."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._session_access = CustomerSessionAccess(sale_expiry)
        self._offer_source = offer_source
        self._plan_explainer = plan_explainer

    def explain_for_session(
        self, credentials: CustomerSessionCredentials, offer_id: str, language: CustomerLanguage
    ) -> ExplanationText:
        """Explains the offer as quoted now for the session's item at the sale price.

        Raises OfferNotFoundError when the offer is not quoted for that item and price.
        """
        with self._unit_of_work_factory() as unit_of_work:
            opened = self._session_access.open_sale(unit_of_work, credentials, self._clock.now())
            item = build_sale_offer_query(opened.sale, find_sale_product(unit_of_work, opened.sale))
        for priced_offer in self._offer_source.discover_offers(item):
            if priced_offer.offer.offer_id == offer_id:
                return self._plan_explainer.explain(
                    ChosenPlan.from_priced_offer(priced_offer), language
                )
        raise OfferNotFoundError("The offer is not quoted for this item and price.")
