"""STUB until Phase 3C: assembles the stub customer flow services around one session store."""

from dataclasses import dataclass

from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.services.customer_flow.stub_customer_advice_service import (
    StubCustomerAdviceService,
)
from emi_copilot.services.customer_flow.stub_customer_consent_service import (
    StubCustomerConsentService,
)
from emi_copilot.services.customer_flow.stub_customer_session_service import (
    StubCustomerSessionService,
)
from emi_copilot.services.customer_flow.stub_customer_session_store import (
    StubCustomerSessionStore,
)
from emi_copilot.services.customer_flow.stub_plan_selection_quoter import StubPlanSelectionQuoter
from emi_copilot.services.customer_flow.stub_priced_offer_source import (
    StubGatewayPricedOfferSource,
)
from emi_copilot.services.plan_advice_service import PlanAdviceService


@dataclass(frozen=True, slots=True)
class StubCustomerFlowServices:
    """STUB until Phase 3C: the three customer flow services sharing one in-memory store."""

    session_service: StubCustomerSessionService
    advice_service: StubCustomerAdviceService
    consent_service: StubCustomerConsentService


def build_stub_customer_flow_services(
    payment_gateway: PaymentGatewayPort,
    financial_profile_port: FinancialProfilePort,
    clock: Clock,
    id_generator: IdGenerator,
) -> StubCustomerFlowServices:
    """Builds the stub services over ports; one call gives one application's own store."""
    store = StubCustomerSessionStore()
    offer_source = StubGatewayPricedOfferSource(payment_gateway)
    session_service = StubCustomerSessionService(store, clock, id_generator)
    return StubCustomerFlowServices(
        session_service=session_service,
        advice_service=StubCustomerAdviceService(
            store, session_service, PlanAdviceService(offer_source), financial_profile_port
        ),
        consent_service=StubCustomerConsentService(
            store, session_service, StubPlanSelectionQuoter(offer_source), clock, id_generator
        ),
    )
