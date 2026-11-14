"""The composition root builds the configured gateway at startup and fails fast (ADR 0004)."""

import pytest
from fastapi.testclient import TestClient

from emi_copilot.adapters.payment_gateway.factory import PaymentGatewayConfigurationError
from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.api.dependencies import (
    ApplicationComponents,
    provide_clock,
    provide_event_bus,
    provide_id_generator,
    provide_payment_gateway,
    provide_unit_of_work_factory,
)
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
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
