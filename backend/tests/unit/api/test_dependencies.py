"""The composition root builds the configured gateway at startup and fails fast (ADR 0004)."""

import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from emi_copilot.adapters.consent_otp.mock_adapter import MockConsentOtpSenderAdapter
from emi_copilot.adapters.customer_contact.mock_adapter import MockPaytmCustomerContactAdapter
from emi_copilot.adapters.financial_profile.mock_adapter import (
    MockSyntheticFinancialProfileAdapter,
)
from emi_copilot.adapters.payment_gateway.factory import PaymentGatewayConfigurationError
from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.api.customer_dependencies import (
    provide_consent_reference_serial_generator,
    provide_customer_contact,
    provide_financial_profile_port,
)
from emi_copilot.api.dependencies import (
    ApplicationComponents,
    provide_clock,
    provide_event_bus,
    provide_id_generator,
    provide_payment_gateway,
    provide_unit_of_work_factory,
)
from emi_copilot.api.merchant_dependencies import (
    provide_access_token_lifetime,
    provide_pin_hasher,
)
from emi_copilot.api.rate_limiting import (
    provide_consent_otp_request_rate_limiter,
    provide_customer_consent_rate_limiter,
    provide_customer_session_start_rate_limiter,
    provide_merchant_payment_rate_limiter,
    provide_pairing_rate_limiter,
    provide_payment_webhook_rate_limiter,
)
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
from emi_copilot.core.consent_reference_serial_generator import (
    RandomConsentReferenceSerialGenerator,
)
from emi_copilot.main import create_application


def test_startup_in_paytm_mode_without_credentials_fails() -> None:
    """Paytm mode never falls back to the Mock: startup itself raises."""
    application = create_application(
        ApplicationSettings(payment_gateway_mode=PaymentGatewayMode.PAYTM)
    )
    with (
        pytest.raises(PaymentGatewayConfigurationError, match="PAYTM_MERCHANT_ID"),
        TestClient(application),
    ):
        pass


def test_startup_in_mock_mode_stores_components_with_the_mock_gateway() -> None:
    """The default mode builds the Mock once and keeps it on app.state, not in a global."""
    application = create_application(ApplicationSettings())
    with TestClient(application):
        components = application.state.application_components
        assert isinstance(components, ApplicationComponents)
        assert isinstance(components.payment_gateway, MockPaymentGatewayAdapter)


def test_component_providers_give_the_components_built_at_startup() -> None:
    """Each provider hands out the one instance stored at startup."""
    application = create_application(ApplicationSettings())
    with TestClient(application):
        components = application.state.application_components
        assert provide_payment_gateway(components) is components.payment_gateway
        assert provide_unit_of_work_factory(components) is components.unit_of_work_factory
        assert provide_clock(components) is components.clock
        assert provide_id_generator(components) is components.id_generator
        assert provide_event_bus(components) is components.event_bus


def test_merchant_providers_give_the_startup_hasher_limiter_and_token_lifetime() -> None:
    """The PIN hasher and pairing limiter are built once; the lifetime comes from settings."""
    application = create_application(
        ApplicationSettings(merchant_access_token_lifetime_in_seconds=3600)
    )
    with TestClient(application):
        components = application.state.application_components
        assert provide_pin_hasher(components) is components.pin_hasher
        assert provide_pairing_rate_limiter(components) is components.pairing_rate_limiter
        assert (
            provide_merchant_payment_rate_limiter(components)
            is components.merchant_payment_rate_limiter
        )
        assert (
            provide_payment_webhook_rate_limiter(components)
            is components.payment_webhook_rate_limiter
        )
        assert provide_access_token_lifetime(components) == timedelta(hours=1)


def test_startup_builds_the_labelled_customer_flow_mocks_and_announces_them(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Profile, phone number and code sender are Mocks, each named in the startup log (rule 10)."""
    application = create_application(ApplicationSettings())
    with caplog.at_level(logging.WARNING), TestClient(application):
        components = application.state.application_components
        assert isinstance(components.financial_profile, MockSyntheticFinancialProfileAdapter)
        assert components.are_financial_profiles_synthetic is True
        assert isinstance(components.customer_contact, MockPaytmCustomerContactAdapter)
        assert isinstance(components.consent_otp.sender, MockConsentOtpSenderAdapter)
        assert provide_financial_profile_port(components) is components.financial_profile
        assert provide_customer_contact(components) is components.customer_contact
    announced_messages = " ".join(record.getMessage() for record in caplog.records)
    for mock_name in (
        "MockSyntheticFinancialProfileAdapter",
        "MockPaytmCustomerContactAdapter",
        "MockConsentOtpSenderAdapter",
    ):
        assert mock_name in announced_messages


def test_customer_rate_limiters_are_built_once_from_their_settings() -> None:
    """Each customer limiter is one startup instance; the serial source is random by default."""
    application = create_application(ApplicationSettings())
    with TestClient(application):
        components = application.state.application_components
        assert (
            provide_customer_session_start_rate_limiter(components)
            is components.customer_session_start_rate_limiter
        )
        assert (
            provide_consent_otp_request_rate_limiter(components)
            is components.consent_otp_request_rate_limiter
        )
        assert (
            provide_customer_consent_rate_limiter(components)
            is components.customer_consent_rate_limiter
        )
    assert isinstance(
        provide_consent_reference_serial_generator(), RandomConsentReferenceSerialGenerator
    )
