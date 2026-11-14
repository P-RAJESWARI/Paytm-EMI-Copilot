"""Providers of the sale services, assembled per request from the startup components.

Kept beside dependencies.py (the composition root) so neither file outgrows its size limit;
the components themselves are still built only there.
"""

from datetime import timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends

from emi_copilot.adapters.payment_gateway.mock_payment_simulator_port import (
    MockPaymentSimulatorPort,
)
from emi_copilot.api.dependencies import (
    ClockDependency,
    ComponentsDependency,
    EventBusDependency,
    GatewayDependency,
    IdGeneratorDependency,
    OfferDiscoveryServiceDependency,
    PaymentHandoffServiceDependency,
    PaymentStatusServiceDependency,
    UnitOfWorkFactoryDependency,
)
from emi_copilot.core.qr_token_signer import QrTokenSigner
from emi_copilot.services.customer_qr_link_issuer import CustomerQrLinkIssuer
from emi_copilot.services.get_sale_service import GetSaleService
from emi_copilot.services.issue_qr_token_service import IssueQrTokenService
from emi_copilot.services.list_counter_sales_service import ListCounterSalesService
from emi_copilot.services.mark_sale_ready_to_pay_service import MarkSaleReadyToPayService
from emi_copilot.services.mock_customer_simulator_service import MockCustomerSimulatorService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.sale_handoff_service import SaleHandoffService
from emi_copilot.services.sale_status_feed_service import SaleStatusFeedService
from emi_copilot.services.start_sale_service import StartSaleService


def provide_customer_qr_link_issuer(
    components: ComponentsDependency, clock: ClockDependency
) -> CustomerQrLinkIssuer:
    """Builds the QR issuer on the startup key, the request's clock and the configured lifetime."""
    settings = components.settings
    return CustomerQrLinkIssuer(
        QrTokenSigner(components.customer_qr_signing_key, clock),
        settings.customer_web_base_url,
        timedelta(seconds=settings.customer_qr_token_lifetime_in_seconds),
    )


def provide_sale_expiry_step(
    components: ComponentsDependency, event_bus: EventBusDependency
) -> SaleExpiryStep:
    """Builds the expiry step with the configured choosing lifetime."""
    return SaleExpiryStep(
        event_bus, timedelta(seconds=components.settings.sale_choosing_expiry_in_seconds)
    )


QrLinkIssuerDependency = Annotated[CustomerQrLinkIssuer, Depends(provide_customer_qr_link_issuer)]
SaleExpiryDependency = Annotated[SaleExpiryStep, Depends(provide_sale_expiry_step)]


def provide_start_sale_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    components: ComponentsDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    event_bus: EventBusDependency,
    qr_link_issuer: QrLinkIssuerDependency,
    sale_expiry: SaleExpiryDependency,
) -> StartSaleService:
    """Assembles the start-sale service with the startup session code generator."""
    return StartSaleService(
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        id_generator=id_generator,
        event_bus=event_bus,
        session_code_generator=components.session_code_generator,
        qr_link_issuer=qr_link_issuer,
        sale_expiry=sale_expiry,
    )


def provide_list_counter_sales_service(
    components: ComponentsDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    sale_expiry: SaleExpiryDependency,
) -> ListCounterSalesService:
    """Assembles the counter list service in the configured reporting time zone."""
    return ListCounterSalesService(
        unit_of_work_factory, clock, sale_expiry, ZoneInfo(components.settings.reporting_time_zone)
    )


def provide_get_sale_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    sale_expiry: SaleExpiryDependency,
) -> GetSaleService:
    """Assembles the single-sale read service."""
    return GetSaleService(unit_of_work_factory, clock, sale_expiry)


def provide_issue_qr_token_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    qr_link_issuer: QrLinkIssuerDependency,
    sale_expiry: SaleExpiryDependency,
) -> IssueQrTokenService:
    """Assembles the QR re-issue service."""
    return IssueQrTokenService(unit_of_work_factory, clock, qr_link_issuer, sale_expiry)


StartSaleServiceDependency = Annotated[StartSaleService, Depends(provide_start_sale_service)]
ListCounterSalesServiceDependency = Annotated[
    ListCounterSalesService, Depends(provide_list_counter_sales_service)
]
GetSaleServiceDependency = Annotated[GetSaleService, Depends(provide_get_sale_service)]
IssueQrTokenServiceDependency = Annotated[
    IssueQrTokenService, Depends(provide_issue_qr_token_service)
]


def provide_sale_handoff_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    components: ComponentsDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    event_bus: EventBusDependency,
    sale_expiry: SaleExpiryDependency,
    payment_handoff_service: PaymentHandoffServiceDependency,
    payment_status_service: PaymentStatusServiceDependency,
) -> SaleHandoffService:
    """Assembles the M4 hand-off service on the two Layer 1 payment services and the stale limit."""
    return SaleHandoffService(
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        event_bus=event_bus,
        sale_expiry=sale_expiry,
        payment_handoff_service=payment_handoff_service,
        payment_status_service=payment_status_service,
        link_creation_stale_after=components.settings.payment_link_creation_stale_after,
    )


SaleHandoffServiceDependency = Annotated[SaleHandoffService, Depends(provide_sale_handoff_service)]


def provide_sale_status_feed_service(
    components: ComponentsDependency, clock: ClockDependency
) -> SaleStatusFeedService:
    """Builds the live feed service on the startup broadcaster and the configured heartbeat."""
    return SaleStatusFeedService(
        components.sale_status_broadcaster,
        clock,
        timedelta(seconds=components.settings.sale_event_stream_heartbeat_interval_in_seconds),
    )


SaleStatusFeedServiceDependency = Annotated[
    SaleStatusFeedService, Depends(provide_sale_status_feed_service)
]


class MockPaymentSimulatorUnavailableError(RuntimeError):
    """Raised when the simulator is asked to pay but the configured gateway is not the Mock."""


def provide_mark_sale_ready_to_pay_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    offer_discovery_service: OfferDiscoveryServiceDependency,
    clock: ClockDependency,
    event_bus: EventBusDependency,
    sale_expiry: SaleExpiryDependency,
) -> MarkSaleReadyToPayService:
    """Assembles the service that records a customer's agreed plan (simulator, then Layer 3)."""
    return MarkSaleReadyToPayService(
        unit_of_work_factory, offer_discovery_service, clock, event_bus, sale_expiry
    )


def provide_mock_payment_simulator(payment_gateway: GatewayDependency) -> MockPaymentSimulatorPort:
    """Gives the Mock gateway's customer controls; any other gateway is a wiring error (500).

    Settings refuse the simulator in paytm mode, so this only fails with a test double.
    """
    if not isinstance(payment_gateway, MockPaymentSimulatorPort):
        raise MockPaymentSimulatorUnavailableError(
            "The Mock customer simulator needs the Mock payment gateway."
        )
    return payment_gateway


MarkSaleReadyToPayServiceDependency = Annotated[
    MarkSaleReadyToPayService, Depends(provide_mark_sale_ready_to_pay_service)
]
MockPaymentSimulatorDependency = Annotated[
    MockPaymentSimulatorPort, Depends(provide_mock_payment_simulator)
]


def provide_mock_customer_simulator_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    mark_sale_ready_to_pay_service: MarkSaleReadyToPayServiceDependency,
    payment_status_service: PaymentStatusServiceDependency,
    mock_payment_simulator: MockPaymentSimulatorDependency,
) -> MockCustomerSimulatorService:
    """Assembles the labelled demo simulator on the services the real flow uses."""
    return MockCustomerSimulatorService(
        unit_of_work_factory,
        mark_sale_ready_to_pay_service,
        payment_status_service,
        mock_payment_simulator,
    )


MockCustomerSimulatorServiceDependency = Annotated[
    MockCustomerSimulatorService, Depends(provide_mock_customer_simulator_service)
]
