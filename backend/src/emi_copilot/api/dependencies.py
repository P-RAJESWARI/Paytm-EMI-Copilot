"""Composition root (ADR 0008): builds every component once at startup and injects them.

This is the only module outside adapters/ that imports the gateway factory. Components live on
app.state, never in module globals. Services are stateless, so they are assembled per request
from the component providers below; a test overrides one provider (for example the gateway)
with app.dependency_overrides and every service that needs it picks the override up.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from functools import partial
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy import Engine

from emi_copilot.adapters.payment_gateway.factory import PaymentGatewayFactory
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.core.clock import Clock, SystemClock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.events.audit_subscriber import AuditSubscriber
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.database import create_database_engine, create_session_factory
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.payment_handoff_service import PaymentHandoffService
from emi_copilot.services.payment_status_service import PaymentStatusService


@dataclass(frozen=True, slots=True)
class ApplicationComponents:
    """Everything built once per process: settings, time, ids, gateway, events and database."""

    settings: ApplicationSettings
    clock: Clock
    id_generator: IdGenerator
    payment_gateway: PaymentGatewayPort
    event_bus: DomainEventBus
    database_engine: Engine
    unit_of_work_factory: UnitOfWorkFactory


def build_application_components(
    settings: ApplicationSettings, id_generator: IdGenerator
) -> ApplicationComponents:
    """Builds the components; paytm mode without credentials raises here, failing startup."""
    clock = SystemClock()
    payment_gateway = PaymentGatewayFactory().create(settings, clock, id_generator)
    event_bus = DomainEventBus()
    AuditSubscriber(id_generator).subscribe_to(event_bus)
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
    )


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


def provide_payment_handoff_service(
    payment_gateway: GatewayDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    event_bus: EventBusDependency,
) -> PaymentHandoffService:
    """Assembles the payment hand-off service from the injected components."""
    return PaymentHandoffService(
        payment_gateway, unit_of_work_factory, clock, id_generator, event_bus
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
