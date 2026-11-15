"""Composition root (ADR 0008): builds every component once at startup and injects them.

This is the only module outside adapters/ that imports the adapter factories (gateway,
settlement, weekly message delivery, customer contact, consent code, AI providers) and the
synthetic profile Mock. Components live on
app.state, never in module globals. Services are stateless, so they are assembled per request
from the component providers below; a test overrides one provider (for example the gateway)
with app.dependency_overrides and every service that needs it picks the override up.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from functools import partial
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy import Engine

from emi_copilot.adapters.ai.factory import AiComponents, AiProviderFactory
from emi_copilot.adapters.consent_otp.factory import ConsentOtpComponents, ConsentOtpFactory
from emi_copilot.adapters.customer_contact.factory import CustomerContactFactory
from emi_copilot.adapters.customer_contact.port import CustomerContactPort
from emi_copilot.adapters.financial_profile.mock_adapter import MockSyntheticFinancialProfileAdapter
from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.adapters.payment_gateway.factory import PaymentGatewayFactory
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.adapters.settlement.factory import SettlementFactory
from emi_copilot.adapters.settlement.port import SettlementPort
from emi_copilot.adapters.weekly_message_delivery.factory import WeeklyMessageDeliveryFactory
from emi_copilot.adapters.weekly_message_delivery.port import WeeklyMessageDeliveryPort
from emi_copilot.api.customer_phone_hash_key import resolve_customer_phone_hash_key
from emi_copilot.api.customer_qr_signing_key import resolve_customer_qr_signing_key
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.core.clock import Clock, SystemClock
from emi_copilot.core.fixed_window_rate_limiter import FixedWindowRateLimiter
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.keyed_hasher import KeyedHasher
from emi_copilot.core.pin_hasher import ScryptPinHasher
from emi_copilot.core.session_code_generator import (
    RandomSessionCodeGenerator,
    SessionCodeGenerator,
)
from emi_copilot.events.audit_subscriber import AuditSubscriber
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.events.funnel_event_recorder import FunnelEventRecorder
from emi_copilot.events.sale_payment_outcome_subscriber import SalePaymentOutcomeSubscriber
from emi_copilot.events.sale_status_broadcaster import SaleStatusBroadcaster
from emi_copilot.repositories.database import create_database_engine, create_session_factory
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.ai.ai_service_state import AiServiceState
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.payment_handoff_service import PaymentHandoffService
from emi_copilot.services.payment_status_service import PaymentStatusService


@dataclass(frozen=True, slots=True)
class ApplicationComponents:
    """Everything built once per process: settings, time, ids, gateway, events and database.

    The PIN hasher (with its decoy hash), the rate limiters, the customer QR signing key,
    the session code generator, the live sale status broadcaster, the report adapters and the
    customer flow's Mock adapters and keyed hasher live here too, because they must outlive one
    request. The key is kept out of repr.
    """

    settings: ApplicationSettings
    clock: Clock
    id_generator: IdGenerator
    payment_gateway: PaymentGatewayPort
    event_bus: DomainEventBus
    database_engine: Engine
    unit_of_work_factory: UnitOfWorkFactory
    pin_hasher: ScryptPinHasher
    pairing_rate_limiter: FixedWindowRateLimiter
    merchant_payment_rate_limiter: FixedWindowRateLimiter
    payment_webhook_rate_limiter: FixedWindowRateLimiter
    customer_qr_signing_key: bytes = field(repr=False)
    session_code_generator: SessionCodeGenerator
    sale_status_broadcaster: SaleStatusBroadcaster
    settlement: SettlementPort
    weekly_message_delivery: WeeklyMessageDeliveryPort
    financial_profile: FinancialProfilePort
    are_financial_profiles_synthetic: bool
    customer_contact: CustomerContactPort
    consent_otp: ConsentOtpComponents
    customer_keyed_hasher: KeyedHasher
    customer_session_start_rate_limiter: FixedWindowRateLimiter
    consent_otp_request_rate_limiter: FixedWindowRateLimiter
    customer_consent_rate_limiter: FixedWindowRateLimiter
    ai: AiComponents
    ai_service_state: AiServiceState


def build_event_bus(
    id_generator: IdGenerator, sale_status_broadcaster: SaleStatusBroadcaster
) -> DomainEventBus:
    """Builds the one event bus: audit, funnel, sale payment rules, then the after-commit feed."""
    event_bus = DomainEventBus()
    AuditSubscriber(id_generator).subscribe_to(event_bus)
    FunnelEventRecorder(id_generator).subscribe_to(event_bus)
    SalePaymentOutcomeSubscriber(event_bus).subscribe()
    sale_status_broadcaster.subscribe_to(event_bus)
    return event_bus


def build_application_components(
    settings: ApplicationSettings, id_generator: IdGenerator
) -> ApplicationComponents:
    """Builds the components; paytm mode without credentials raises here, failing startup.

    So does paytm mode without CUSTOMER_QR_SIGNING_SECRET or CUSTOMER_PHONE_HASH_SECRET, a
    secret that is too short, and paytm mode at all while the customer's phone number and
    consent codes have only Mock sources, and an AI provider in sarvam mode (no key, or not yet
    built). Every Mock adapter announces itself as it is built.
    """
    clock = SystemClock()
    payment_gateway = PaymentGatewayFactory().create(settings, clock, id_generator)
    customer_qr_signing_key = resolve_customer_qr_signing_key(settings)
    customer_contact = CustomerContactFactory(settings).create()
    consent_otp = ConsentOtpFactory(settings).create()
    ai_components = AiProviderFactory().create(settings.ai_settings, clock)
    sale_status_broadcaster = SaleStatusBroadcaster(
        settings.sale_event_stream_maximum_queued_messages
    )
    event_bus = build_event_bus(id_generator, sale_status_broadcaster)
    database_engine = create_database_engine(settings)
    session_factory = create_session_factory(database_engine)
    return ApplicationComponents(
        settings=settings,
        clock=clock,
        id_generator=id_generator,
        payment_gateway=payment_gateway,
        event_bus=event_bus,
        database_engine=database_engine,
        unit_of_work_factory=partial(SqlAlchemyUnitOfWork, session_factory, clock),
        pin_hasher=ScryptPinHasher(),
        pairing_rate_limiter=build_rate_limiter(
            clock,
            settings.merchant_pairing_rate_limit_max_requests,
            settings.merchant_pairing_rate_limit_window_in_seconds,
        ),
        merchant_payment_rate_limiter=build_rate_limiter(
            clock,
            settings.merchant_payment_rate_limit_max_requests,
            settings.merchant_payment_rate_limit_window_in_seconds,
        ),
        payment_webhook_rate_limiter=build_rate_limiter(
            clock,
            settings.payment_webhook_rate_limit_max_requests,
            settings.payment_webhook_rate_limit_window_in_seconds,
        ),
        customer_qr_signing_key=customer_qr_signing_key,
        session_code_generator=RandomSessionCodeGenerator(),
        sale_status_broadcaster=sale_status_broadcaster,
        settlement=SettlementFactory().create(),
        weekly_message_delivery=WeeklyMessageDeliveryFactory().create(),
        financial_profile=MockSyntheticFinancialProfileAdapter(settings.mock_financial_profile),
        are_financial_profiles_synthetic=True,
        customer_contact=customer_contact,
        consent_otp=consent_otp,
        customer_keyed_hasher=KeyedHasher(resolve_customer_phone_hash_key(settings)),
        customer_session_start_rate_limiter=build_rate_limiter(
            clock,
            settings.customer_session_start_rate_limit_max_requests,
            settings.customer_session_start_rate_limit_window_in_seconds,
        ),
        consent_otp_request_rate_limiter=build_rate_limiter(
            clock,
            settings.consent_otp_request_rate_limit_max_requests,
            settings.consent_otp_request_rate_limit_window_in_seconds,
        ),
        customer_consent_rate_limiter=build_rate_limiter(
            clock,
            settings.customer_consent_rate_limit_max_requests,
            settings.customer_consent_rate_limit_window_in_seconds,
        ),
        ai=ai_components,
        ai_service_state=AiServiceState.build(clock),
    )


def build_rate_limiter(
    clock: Clock, maximum_requests: int, window_in_seconds: int
) -> FixedWindowRateLimiter:
    """Builds one in-memory limiter: at most the given requests per key in each window."""
    return FixedWindowRateLimiter(clock, maximum_requests, timedelta(seconds=window_in_seconds))


def build_application_lifespan(
    settings: ApplicationSettings, id_generator: IdGenerator
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Gives the lifespan that builds the components at startup and disposes the engine after."""

    @asynccontextmanager
    async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Stores the components on app.state for the providers, then releases the pool."""
        components = build_application_components(settings, id_generator)
        application.state.application_components = components
        try:
            yield
        finally:
            components.database_engine.dispose()

    return application_lifespan


def provide_application_components(request: Request) -> ApplicationComponents:
    """Gives the components the lifespan stored at startup."""
    components: ApplicationComponents = request.app.state.application_components
    return components


ComponentsDependency = Annotated[ApplicationComponents, Depends(provide_application_components)]


def provide_payment_gateway(components: ComponentsDependency) -> PaymentGatewayPort:
    """Gives the configured payment gateway port (the Mock by default)."""
    return components.payment_gateway


def provide_unit_of_work_factory(components: ComponentsDependency) -> UnitOfWorkFactory:
    """Gives the factory of database units of work."""
    return components.unit_of_work_factory


def provide_clock(components: ComponentsDependency) -> Clock:
    """Gives the clock services stamp events with."""
    return components.clock


def provide_id_generator(components: ComponentsDependency) -> IdGenerator:
    """Gives the generator of order, attempt and delivery ids."""
    return components.id_generator


def provide_event_bus(components: ComponentsDependency) -> DomainEventBus:
    """Gives the event bus the audit subscriber listens on."""
    return components.event_bus


GatewayDependency = Annotated[PaymentGatewayPort, Depends(provide_payment_gateway)]
UnitOfWorkFactoryDependency = Annotated[UnitOfWorkFactory, Depends(provide_unit_of_work_factory)]
ClockDependency = Annotated[Clock, Depends(provide_clock)]
IdGeneratorDependency = Annotated[IdGenerator, Depends(provide_id_generator)]
EventBusDependency = Annotated[DomainEventBus, Depends(provide_event_bus)]


def provide_offer_discovery_service(
    payment_gateway: GatewayDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    event_bus: EventBusDependency,
) -> OfferDiscoveryService:
    """Assembles the offer discovery service from the injected components."""
    return OfferDiscoveryService(payment_gateway, unit_of_work_factory, clock, event_bus)


def provide_payment_handoff_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    components: ComponentsDependency,
    payment_gateway: GatewayDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    event_bus: EventBusDependency,
) -> PaymentHandoffService:
    """Assembles the payment hand-off service with its stale limit from the gateway timeouts."""
    return PaymentHandoffService(
        payment_gateway,
        unit_of_work_factory,
        clock,
        id_generator,
        event_bus,
        link_creation_stale_after=components.settings.payment_link_creation_stale_after,
    )


def provide_payment_status_service(
    payment_gateway: GatewayDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    event_bus: EventBusDependency,
) -> PaymentStatusService:
    """Assembles the payment status service from the injected components."""
    return PaymentStatusService(
        payment_gateway, unit_of_work_factory, clock, id_generator, event_bus
    )


OfferDiscoveryServiceDependency = Annotated[
    OfferDiscoveryService, Depends(provide_offer_discovery_service)
]
PaymentHandoffServiceDependency = Annotated[
    PaymentHandoffService, Depends(provide_payment_handoff_service)
]
PaymentStatusServiceDependency = Annotated[
    PaymentStatusService, Depends(provide_payment_status_service)
]
