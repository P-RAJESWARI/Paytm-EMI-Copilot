"""CustomerPlanService: C4's plan comparison and C6's alternatives for a customer's own sale."""

from dataclasses import dataclass

from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.core.clock import Clock
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.customer_sessions import ComfortCheckStatus, CustomerSession
from emi_copilot.domain.events import CustomerPlansViewed
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery
from emi_copilot.domain.sales import Sale
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory
from emi_copilot.services.customer.customer_session_access import (
    CustomerSessionAccess,
    build_sale_offer_query,
    find_sale_product,
    require_confirmed_budget,
)
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.plan_advice_service import PlanAdviceService
from emi_copilot.services.plan_advice_types import (
    AlternativesAdvice,
    CheaperModelCandidate,
    PlanComparison,
)
from emi_copilot.services.sale_expiry import SaleExpiryStep


@dataclass(frozen=True, slots=True)
class _AdviceInputs:
    """What one advice request needs, read in one short transaction."""

    session: CustomerSession
    sale: Sale
    item: OfferDiscoveryQuery
    monthly_budget: Money
    cheaper_models: tuple[CheaperModelCandidate, ...]


def find_cheaper_model(
    unit_of_work: UnitOfWork, sale: Sale, product: CatalogueProduct
) -> CheaperModelCandidate | None:
    """Gives C6's cheaper model: the dearest of the shop's products below the sale's price.

    A candidate has the same gateway brand and category as the sale's product, so it is the
    same kind of item (the 64 GB model of the 128 GB phone); None when the shop has none.
    """
    cheaper_products = [
        candidate
        for candidate in unit_of_work.products.list_for_merchant(sale.merchant_id)
        if candidate.id != product.id
        and candidate.gateway_brand_id == product.gateway_brand_id
        and candidate.gateway_category_id == product.gateway_category_id
        and candidate.list_price < sale.price
    ]
    if not cheaper_products:
        return None
    dearest = max(cheaper_products, key=lambda candidate: (candidate.list_price, candidate.id))
    return CheaperModelCandidate(
        product_id=dearest.id,
        product_name=dearest.name,
        price=dearest.list_price,
        brand_id=dearest.gateway_brand_id,
        category_id=dearest.gateway_category_id,
        gateway_product_id=dearest.gateway_product_id,
    )


class CustomerPlanService:
    """Quotes every plan for the sale's product at the sale's price, through the audited path.

    The offers come from Layer 1's OfferDiscoveryService (through PlanAdviceService); no plan is
    ever hidden. Comfort is assessed only when the customer completed the comfort check. The
    first time a sale's plans are shown is announced for the funnel (PLANS_VIEWED).
    """

    def __init__(  # noqa: PLR0913 - a use case wired with its collaborators, by keyword
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        event_bus: DomainEventBus,
        sale_expiry: SaleExpiryStep,
        plan_advice_service: PlanAdviceService,
        financial_profile_port: FinancialProfilePort,
    ) -> None:
        """Keeps the collaborators of plan advice for one customer session."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._event_bus = event_bus
        self._session_access = CustomerSessionAccess(sale_expiry)
        self._plan_advice_service = plan_advice_service
        self._financial_profile_port = financial_profile_port

    def compare_plans(self, credentials: CustomerSessionCredentials) -> PlanComparison:
        """Ranks every plan for the confirmed budget (C4), then announces that it was shown."""
        inputs = self._read_advice_inputs(credentials, include_cheaper_model=False)
        comparison = self._plan_advice_service.compare_plans(
            inputs.item, inputs.monthly_budget, self._read_financial_profile(inputs.session)
        )
        with self._unit_of_work_factory() as unit_of_work:
            # The sale lock makes two first views take turns, so the funnel counts one.
            unit_of_work.sales.find_by_id_for_update(inputs.sale.id)
            self._event_bus.publish(
                CustomerPlansViewed(
                    occurred_at=self._clock.now(),
                    sale_id=inputs.sale.id,
                    merchant_id=inputs.sale.merchant_id,
                ),
                unit_of_work,
            )
        return comparison

    def suggest_alternatives(
        self, credentials: CustomerSessionCredentials, chosen_offer_id: str
    ) -> AlternativesAdvice:
        """Finds C6's down payment, longer tenure and cheaper model options for a chosen plan.

        Only a longer tenure can be consented to; the other two need the shop (ADR 0022).
        """
        inputs = self._read_advice_inputs(credentials, include_cheaper_model=True)
        return self._plan_advice_service.suggest_alternatives(
            inputs.item,
            chosen_offer_id,
            inputs.monthly_budget,
            self._read_financial_profile(inputs.session),
            inputs.cheaper_models,
        )

    def _read_advice_inputs(
        self, credentials: CustomerSessionCredentials, *, include_cheaper_model: bool
    ) -> _AdviceInputs:
        """Reads the session, budget and product while CHOOSING; refusals raise after commit."""
        with self._unit_of_work_factory() as unit_of_work:
            opened = self._session_access.open_sale(unit_of_work, credentials, self._clock.now())
            refusal = opened.find_choosing_refusal()
            if refusal is None:
                product = find_sale_product(unit_of_work, opened.sale)
                cheaper_model = (
                    find_cheaper_model(unit_of_work, opened.sale, product)
                    if include_cheaper_model
                    else None
                )
                return _AdviceInputs(
                    session=opened.session,
                    sale=opened.sale,
                    item=build_sale_offer_query(opened.sale, product),
                    monthly_budget=require_confirmed_budget(opened.session),
                    cheaper_models=() if cheaper_model is None else (cheaper_model,),
                )
        raise refusal

    def _read_financial_profile(self, session: CustomerSession) -> FinancialProfile | None:
        """Reads the profile only when the customer completed the comfort check, else None."""
        if session.comfort_check_status is not ComfortCheckStatus.COMPLETED:
            return None
        return self._financial_profile_port.get_financial_profile(session.id)
