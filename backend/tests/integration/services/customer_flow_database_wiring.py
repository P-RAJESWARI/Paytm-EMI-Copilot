"""Wires the customer flow services on the test database, the Mock gateway and the real bus."""

from dataclasses import dataclass
from functools import partial

from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.api.dependencies import build_event_bus
from emi_copilot.core.qr_token_signer import QrTokenSigner, hash_qr_token_nonce
from emi_copilot.domain.customer_sessions import CustomerSession
from emi_copilot.domain.funnel import FunnelEvent
from emi_copilot.domain.money import Money
from emi_copilot.domain.sales import Sale, SessionCode
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.events.sale_status_broadcaster import SaleStatusBroadcaster
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.customer.customer_choice_service import CustomerChoiceService
from emi_copilot.services.customer.customer_plan_service import CustomerPlanService
from emi_copilot.services.customer.customer_session_service import CustomerSessionService
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.plan_advice_service import PlanAdviceService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.merchant_builders import MERCHANT_ID, build_catalogue_product, build_merchant
from tests.sale_builders import CHOOSING_LIFETIME, build_qr_token_state, build_sale
from tests.unit.services.customer.customer_service_wiring import (
    PHONE_64_GB_PRODUCT_ID,
    QR_SIGNING_KEY,
    SESSION_LIFETIME,
    RecordingFinancialProfilePort,
    SequentialSessionTokenIssuer,
)

MOCK_GATEWAY_SIGNING_KEY = b"integration-test-mock-signing-key-32b"  # pragma: allowlist secret
DESIGN_SALE_IDS = ("01JCSALE000000000000000001", "01JCSALE000000000000000002")
"""Two CHOOSING sales of the 128 GB phone, with session codes 4821 and 4822."""


def nonce_for(sale_id: str) -> str:
    """Gives the nonce of the QR token stored on one design sale."""
    return f"synthetic-nonce-{sale_id[-4:]}"


@dataclass
class DatabaseCustomerServices:
    """The customer services on PostgreSQL, the shared doubles, and readers of what they stored."""

    sessions: CustomerSessionService
    choices: CustomerChoiceService
    plans: CustomerPlanService
    qr_token_signer: QrTokenSigner
    unit_of_work_factory: UnitOfWorkFactory
    event_bus: DomainEventBus
    sale_expiry: SaleExpiryStep
    offer_discovery: OfferDiscoveryService
    financial_profile_port: RecordingFinancialProfilePort
    clock: FixedClock

    def read_sale(self, sale_id: str) -> Sale | None:
        """Reads one stored sale in a fresh transaction."""
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.sales.find_by_id_for_merchant(MERCHANT_ID, sale_id)

    def read_session(self, customer_session_id: str) -> CustomerSession | None:
        """Reads one stored customer session in a fresh transaction."""
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.customer_sessions.find_by_id_for_update(customer_session_id)

    def read_funnel_events(self, sale_id: str) -> tuple[FunnelEvent, ...]:
        """Reads the funnel rows of one sale, oldest first."""
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.funnel_events.list_for_sale(sale_id)


def store_design_shop(session_factory: sessionmaker[Session], clock: FixedClock) -> None:
    """Commits Ravi Electronics, its 128 GB and 64 GB phones and two CHOOSING 128 GB sales."""
    with SqlAlchemyUnitOfWork(session_factory, clock) as unit_of_work:
        unit_of_work.merchants.add(build_merchant(display_name="Ravi Electronics"))
        unit_of_work.products.add(
            build_catalogue_product(gateway_product_id=MOCK_PHONE_128_GB_PRODUCT_ID)
        )
        unit_of_work.products.add(
            build_catalogue_product(
                id=PHONE_64_GB_PRODUCT_ID,
                name="Example phone, 64 GB",
                list_price=Money.from_rupees(18000),
                gateway_product_id=MOCK_PHONE_64_GB_PRODUCT_ID,
            )
        )
        for position, sale_id in enumerate(DESIGN_SALE_IDS):
            unit_of_work.sales.add(
                build_sale(
                    id=sale_id,
                    session_code=SessionCode(f"482{position + 1}"),
                    qr_token=build_qr_token_state(
                        nonce_hash=hash_qr_token_nonce(nonce_for(sale_id))
                    ),
                )
            )


def wire_database_customer_services(
    session_factory: sessionmaker[Session], clock: FixedClock
) -> DatabaseCustomerServices:
    """Stores the design shop, then wires the services as the composition root will."""
    store_design_shop(session_factory, clock)
    unit_of_work_factory = partial(SqlAlchemyUnitOfWork, session_factory, clock)
    event_bus = build_event_bus(SequentialIdGenerator("01JCEVENTROW"), SaleStatusBroadcaster(10))
    expiry = SaleExpiryStep(event_bus, CHOOSING_LIFETIME)
    offer_discovery = OfferDiscoveryService(
        MockPaymentGatewayAdapter(clock, MOCK_GATEWAY_SIGNING_KEY),
        unit_of_work_factory,
        clock,
        event_bus,
    )
    signer = QrTokenSigner(QR_SIGNING_KEY, clock)
    profile_port = RecordingFinancialProfilePort()
    return DatabaseCustomerServices(
        sessions=CustomerSessionService(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
            event_bus=event_bus,
            qr_token_signer=signer,
            id_generator=SequentialIdGenerator("01JCSESSIONROW"),
            sale_expiry=expiry,
            session_lifetime=SESSION_LIFETIME,
            session_token_issuer=SequentialSessionTokenIssuer(),
        ),
        choices=CustomerChoiceService(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
            event_bus=event_bus,
            sale_expiry=expiry,
            financial_profile_port=profile_port,
            are_financial_profiles_synthetic=True,
        ),
        plans=CustomerPlanService(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
            event_bus=event_bus,
            sale_expiry=expiry,
            plan_advice_service=PlanAdviceService(offer_discovery),
            financial_profile_port=profile_port,
        ),
        qr_token_signer=signer,
        unit_of_work_factory=unit_of_work_factory,
        event_bus=event_bus,
        sale_expiry=expiry,
        offer_discovery=offer_discovery,
        financial_profile_port=profile_port,
        clock=clock,
    )
