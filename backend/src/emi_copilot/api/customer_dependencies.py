"""Providers of the customer flow services, assembled per request from the startup components.

The session credentials and the customer's language are read in customer_request_context.py.
Kept beside dependencies.py (the composition root) so neither file outgrows its size limit; the
components themselves (Mock adapters, keyed hasher, limiters) are still built only there. Each
service is assembled per request from overridable providers, so tests can swap one collaborator.
"""

from datetime import timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends

from emi_copilot.adapters.customer_contact.port import CustomerContactPort
from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.api.ai_dependencies import (
    PlanExplainerDependency,
    ShownExplanationCacheDependency,
)
from emi_copilot.api.dependencies import (
    ClockDependency,
    ComponentsDependency,
    EventBusDependency,
    IdGeneratorDependency,
    OfferDiscoveryServiceDependency,
    UnitOfWorkFactoryDependency,
)
from emi_copilot.api.sale_dependencies import SaleExpiryDependency
from emi_copilot.core.consent_reference_serial_generator import (
    ConsentReferenceSerialGenerator,
    RandomConsentReferenceSerialGenerator,
)
from emi_copilot.core.qr_token_signer import QrTokenSigner
from emi_copilot.services.customer.consent_otp_service import ConsentOtpService
from emi_copilot.services.customer.customer_choice_service import CustomerChoiceService
from emi_copilot.services.customer.customer_consent_service import CustomerConsentService
from emi_copilot.services.customer.customer_explanation_service import CustomerExplanationService
from emi_copilot.services.customer.customer_plan_service import CustomerPlanService
from emi_copilot.services.customer.customer_receipt_service import CustomerReceiptService
from emi_copilot.services.customer.customer_session_service import CustomerSessionService
from emi_copilot.services.customer.session_plan_finder import SessionPlanFinder
from emi_copilot.services.plan_advice_service import PlanAdviceService


def provide_financial_profile_port(components: ComponentsDependency) -> FinancialProfilePort:
    """Gives the profile source of the consented comfort check (the labelled synthetic Mock)."""
    return components.financial_profile


def provide_customer_contact(components: ComponentsDependency) -> CustomerContactPort:
    """Gives the source of the customer's phone number (the labelled Mock, ADR 0022)."""
    return components.customer_contact


def provide_consent_reference_serial_generator() -> ConsentReferenceSerialGenerator:
    """Gives the random serial source of consent references; tests override it with a fixed one."""
    return RandomConsentReferenceSerialGenerator()


def provide_plan_advice_service(
    offer_discovery_service: OfferDiscoveryServiceDependency,
) -> PlanAdviceService:
    """Assembles plan advice on Layer 1's audited offer discovery."""
    return PlanAdviceService(offer_discovery_service)


FinancialProfileDependency = Annotated[
    FinancialProfilePort, Depends(provide_financial_profile_port)
]
CustomerContactDependency = Annotated[CustomerContactPort, Depends(provide_customer_contact)]
ConsentReferenceSerialGeneratorDependency = Annotated[
    ConsentReferenceSerialGenerator, Depends(provide_consent_reference_serial_generator)
]
PlanAdviceServiceDependency = Annotated[PlanAdviceService, Depends(provide_plan_advice_service)]


def provide_customer_session_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    components: ComponentsDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    event_bus: EventBusDependency,
    sale_expiry: SaleExpiryDependency,
) -> CustomerSessionService:
    """Assembles the QR exchange and session service on the startup QR key and session lifetime."""
    return CustomerSessionService(
        unit_of_work_factory=unit_of_work_factory,
        qr_token_signer=QrTokenSigner(components.customer_qr_signing_key, clock),
        clock=clock,
        id_generator=id_generator,
        event_bus=event_bus,
        sale_expiry=sale_expiry,
        session_lifetime=timedelta(
            seconds=components.settings.customer_session_lifetime_in_seconds
        ),
    )


def provide_customer_choice_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    components: ComponentsDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    event_bus: EventBusDependency,
    sale_expiry: SaleExpiryDependency,
    financial_profile_port: FinancialProfileDependency,
) -> CustomerChoiceService:
    """Assembles the budget and comfort check choice service."""
    return CustomerChoiceService(
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        event_bus=event_bus,
        sale_expiry=sale_expiry,
        financial_profile_port=financial_profile_port,
        are_financial_profiles_synthetic=components.are_financial_profiles_synthetic,
    )


def provide_customer_plan_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    event_bus: EventBusDependency,
    sale_expiry: SaleExpiryDependency,
    plan_advice_service: PlanAdviceServiceDependency,
    financial_profile_port: FinancialProfileDependency,
) -> CustomerPlanService:
    """Assembles the C4 plans and C6 alternatives service."""
    return CustomerPlanService(
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        event_bus=event_bus,
        sale_expiry=sale_expiry,
        plan_advice_service=plan_advice_service,
        financial_profile_port=financial_profile_port,
    )


def provide_consent_otp_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    components: ComponentsDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    sale_expiry: SaleExpiryDependency,
    customer_contact: CustomerContactDependency,
) -> ConsentOtpService:
    """Assembles the one-time code service with the startup sender, generator and code rules."""
    settings = components.settings
    return ConsentOtpService(
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        id_generator=id_generator,
        sale_expiry=sale_expiry,
        customer_contact=customer_contact,
        code_generator=components.consent_otp.code_generator,
        code_sender=components.consent_otp.sender,
        keyed_hasher=components.customer_keyed_hasher,
        otp_lifetime=timedelta(seconds=settings.consent_otp_lifetime_in_seconds),
        otp_resend_wait=timedelta(seconds=settings.consent_otp_resend_wait_in_seconds),
        otp_maximum_attempts=settings.consent_otp_maximum_attempts,
    )


def provide_customer_consent_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    components: ComponentsDependency,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    event_bus: EventBusDependency,
    sale_expiry: SaleExpiryDependency,
    offer_discovery_service: OfferDiscoveryServiceDependency,
    customer_contact: CustomerContactDependency,
    serial_generator: ConsentReferenceSerialGeneratorDependency,
) -> CustomerConsentService:
    """Assembles consent with the startup hasher and the shop's time zone for the reference."""
    return CustomerConsentService(
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        id_generator=id_generator,
        event_bus=event_bus,
        sale_expiry=sale_expiry,
        offer_source=offer_discovery_service,
        customer_contact=customer_contact,
        keyed_hasher=components.customer_keyed_hasher,
        consent_reference_serial_generator=serial_generator,
        consent_time_zone=ZoneInfo(components.settings.reporting_time_zone),
    )


def provide_customer_receipt_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    sale_expiry: SaleExpiryDependency,
) -> CustomerReceiptService:
    """Assembles the C10 receipt service."""
    return CustomerReceiptService(unit_of_work_factory, clock, sale_expiry)


def provide_session_plan_finder(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    sale_expiry: SaleExpiryDependency,
    offer_discovery_service: OfferDiscoveryServiceDependency,
) -> SessionPlanFinder:
    """Assembles the lookup of one of the session's plans as quoted now."""
    return SessionPlanFinder(unit_of_work_factory, clock, sale_expiry, offer_discovery_service)


SessionPlanFinderDependency = Annotated[SessionPlanFinder, Depends(provide_session_plan_finder)]


def provide_customer_explanation_service(
    plan_finder: SessionPlanFinderDependency,
    plan_explainer: PlanExplainerDependency,
    shown_explanation_cache: ShownExplanationCacheDependency,
    id_generator: IdGeneratorDependency,
) -> CustomerExplanationService:
    """Assembles the C7 explanation on the audited AI explainer and the shown-text cache."""
    return CustomerExplanationService(
        plan_finder, plan_explainer, shown_explanation_cache, id_generator
    )


CustomerSessionServiceDependency = Annotated[
    CustomerSessionService, Depends(provide_customer_session_service)
]
CustomerChoiceServiceDependency = Annotated[
    CustomerChoiceService, Depends(provide_customer_choice_service)
]
CustomerPlanServiceDependency = Annotated[
    CustomerPlanService, Depends(provide_customer_plan_service)
]
ConsentOtpServiceDependency = Annotated[ConsentOtpService, Depends(provide_consent_otp_service)]
CustomerConsentServiceDependency = Annotated[
    CustomerConsentService, Depends(provide_customer_consent_service)
]
CustomerReceiptServiceDependency = Annotated[
    CustomerReceiptService, Depends(provide_customer_receipt_service)
]
CustomerExplanationServiceDependency = Annotated[
    CustomerExplanationService, Depends(provide_customer_explanation_service)
]
