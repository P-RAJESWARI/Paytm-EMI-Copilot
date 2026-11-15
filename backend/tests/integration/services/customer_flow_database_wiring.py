"""Wires the customer flow services on the test database, the Mock gateway and the real bus."""

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.api.dependencies import build_event_bus
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.core.keyed_hasher import KeyedHasher
from emi_copilot.core.qr_token_signer import QrTokenSigner, hash_qr_token_nonce
from emi_copilot.domain.consent import ConsentRecord, OtpChallenge
from emi_copilot.domain.customer_sessions import CustomerSession
from emi_copilot.domain.funnel import FunnelEvent
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType, OfferDiscoveryQuery, PricedEmiOffer
from emi_copilot.domain.sales import Sale, SessionCode
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.events.sale_status_broadcaster import SaleStatusBroadcaster
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.ai.shown_explanation_cache import ShownExplanationCache
from emi_copilot.services.customer.consent_otp_service import ConsentOtpService
from emi_copilot.services.customer.customer_choice_service import CustomerChoiceService
from emi_copilot.services.customer.customer_consent_service import CustomerConsentService
from emi_copilot.services.customer.customer_explanation_service import CustomerExplanationService
from emi_copilot.services.customer.customer_plan_service import CustomerPlanService
from emi_copilot.services.customer.customer_receipt_service import CustomerReceiptService
from emi_copilot.services.customer.customer_session_service import CustomerSessionService
from emi_copilot.services.customer.session_plan_finder import SessionPlanFinder
from emi_copilot.services.customer.template_explanation_service import (
    TemplateExplanationService,
)
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.plan_advice_service import PlanAdviceService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from tests.fakes.fake_customer_flow_ports import (
    FakeCustomerContact,
    FixedConsentOtpCodeGenerator,
    FixedConsentReferenceSerialGenerator,
    RecordingConsentOtpSender,
    RecordingFinancialProfilePort,
    SequentialSessionTokenIssuer,
)
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.merchant_builders import MERCHANT_ID, build_catalogue_product, build_merchant
from tests.sale_builders import CHOOSING_LIFETIME, build_qr_token_state, build_sale
from tests.unit.services.customer.customer_service_wiring import (
    INDIA_TIME_ZONE,
    OTP_LIFETIME,
    OTP_MAXIMUM_ATTEMPTS,
    OTP_RESEND_WAIT,
    PHONE_64_GB_PRODUCT_ID,
    PHONE_HASH_KEY,
    QR_SIGNING_KEY,
    SESSION_LIFETIME,
)

MOCK_GATEWAY_SIGNING_KEY = b"integration-test-mock-signing-key-32b"  # pragma: allowlist secret
DESIGN_SALE_IDS = ("01JCSALE000000000000000001", "01JCSALE000000000000000002")
"""Two CHOOSING sales of the 128 GB phone, with session codes 4821 and 4822."""


def nonce_for(sale_id: str) -> str:
    """Gives the nonce of the QR token stored on one design sale."""
    return f"synthetic-nonce-{sale_id[-4:]}"


@dataclass
class HookedOfferSource:
    """The audited offer source, with a hook a test runs after each quote (between transactions)."""

    offer_discovery: OfferDiscoveryService
    after_quote: Callable[[], None] | None = field(default=None)

    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[PricedEmiOffer, ...]:
        """Quotes through OfferDiscoveryService, then runs the hook once, if any."""
        priced_offers = self.offer_discovery.discover_offers(query)
        hook, self.after_quote = self.after_quote, None
        if hook is not None:
            hook()
        return priced_offers


@dataclass
class DatabaseCustomerServices:
    """The customer services on PostgreSQL, the shared doubles, and readers of what they stored."""

    sessions: CustomerSessionService
    choices: CustomerChoiceService
    plans: CustomerPlanService
    otp: ConsentOtpService
    consent: CustomerConsentService
    receipt: CustomerReceiptService
    explanation: CustomerExplanationService
    qr_token_signer: QrTokenSigner
    unit_of_work_factory: Callable[[], SqlAlchemyUnitOfWork]
    hooked_offer_source: HookedOfferSource
    clock: FixedClock

    def read_consent_chain(self) -> tuple[ConsentRecord, ...]:
        """Reads the whole consent chain from the first record."""
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.consent_records.list_in_order()

    def read_latest_challenge(self, customer_session_id: str) -> OtpChallenge | None:
        """Reads the session's latest one-time code challenge."""
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.otp_challenges.find_latest_for_session_for_update(
                customer_session_id
            )

    def read_audit_types(self, subject_type: str, subject_id: str) -> list[AuditEventType]:
        """Reads the audit types about one subject, oldest first."""
        with self.unit_of_work_factory() as unit_of_work:
            return [
                audit_event.event_type
                for audit_event in unit_of_work.audit_events.list_for_subject(
                    subject_type, subject_id
                )
            ]

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
    offer_source = HookedOfferSource(
        OfferDiscoveryService(
            MockPaymentGatewayAdapter(clock, MOCK_GATEWAY_SIGNING_KEY),
            unit_of_work_factory,
            clock,
            event_bus,
        )
    )
    return DatabaseCustomerServices(
        **_wire_session_services(unit_of_work_factory, clock, event_bus, expiry, offer_source),
        **_wire_consent_services(unit_of_work_factory, clock, event_bus, expiry, offer_source),
        qr_token_signer=QrTokenSigner(QR_SIGNING_KEY, clock),
        unit_of_work_factory=unit_of_work_factory,
        hooked_offer_source=offer_source,
        clock=clock,
    )


def _wire_session_services(
    unit_of_work_factory: UnitOfWorkFactory,
    clock: FixedClock,
    event_bus: DomainEventBus,
    expiry: SaleExpiryStep,
    offer_source: HookedOfferSource,
) -> dict[str, Any]:
    """Builds the session, choice and plan services."""
    profile_port = RecordingFinancialProfilePort()
    return {
        "sessions": CustomerSessionService(
            unit_of_work_factory=unit_of_work_factory,
            qr_token_signer=QrTokenSigner(QR_SIGNING_KEY, clock),
            clock=clock,
            id_generator=SequentialIdGenerator("01JCSESSIONROW"),
            event_bus=event_bus,
            sale_expiry=expiry,
            session_lifetime=SESSION_LIFETIME,
            session_token_issuer=SequentialSessionTokenIssuer(),
        ),
        "choices": CustomerChoiceService(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
            event_bus=event_bus,
            sale_expiry=expiry,
            financial_profile_port=profile_port,
            are_financial_profiles_synthetic=True,
        ),
        "plans": CustomerPlanService(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
            event_bus=event_bus,
            sale_expiry=expiry,
            plan_advice_service=PlanAdviceService(offer_source),
            financial_profile_port=profile_port,
        ),
    }


def _wire_consent_services(
    unit_of_work_factory: UnitOfWorkFactory,
    clock: FixedClock,
    event_bus: DomainEventBus,
    expiry: SaleExpiryStep,
    offer_source: HookedOfferSource,
) -> dict[str, Any]:
    """Builds the code, consent, receipt and explanation services."""
    keyed_hasher = KeyedHasher(PHONE_HASH_KEY)
    customer_contact = FakeCustomerContact()
    id_generator = SequentialIdGenerator("01JCCONSENTROW")
    return {
        "otp": ConsentOtpService(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
            id_generator=id_generator,
            sale_expiry=expiry,
            customer_contact=customer_contact,
            code_generator=FixedConsentOtpCodeGenerator(),
            code_sender=RecordingConsentOtpSender(),
            keyed_hasher=keyed_hasher,
            otp_lifetime=OTP_LIFETIME,
            otp_resend_wait=OTP_RESEND_WAIT,
            otp_maximum_attempts=OTP_MAXIMUM_ATTEMPTS,
        ),
        "consent": CustomerConsentService(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
            id_generator=id_generator,
            event_bus=event_bus,
            sale_expiry=expiry,
            offer_source=offer_source,
            customer_contact=customer_contact,
            keyed_hasher=keyed_hasher,
            consent_reference_serial_generator=FixedConsentReferenceSerialGenerator(),
            consent_time_zone=INDIA_TIME_ZONE,
        ),
        "receipt": CustomerReceiptService(unit_of_work_factory, clock, expiry),
        "explanation": CustomerExplanationService(
            SessionPlanFinder(unit_of_work_factory, clock, expiry, offer_source),
            TemplateExplanationService(format_paise_as_whole_rupees),
            ShownExplanationCache(clock),
            id_generator,
        ),
    }
