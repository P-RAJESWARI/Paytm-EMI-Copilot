"""The contact Mock announces itself and gives one synthetic number ending 42."""

import logging

import pytest

from emi_copilot.adapters.customer_contact.factory import (
    CustomerContactConfigurationError,
    CustomerContactFactory,
)
from emi_copilot.adapters.customer_contact.mock_adapter import (
    MOCK_CUSTOMER_CONTACT_ACTIVE_WARNING,
    SYNTHETIC_CUSTOMER_PHONE_NUMBER,
    MockPaytmCustomerContactAdapter,
)
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode


def test_contact_factory_builds_the_mock_and_it_warns_at_startup(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only the labelled Mock exists until Paytm confirms a source (ADR 0022 decision 2)."""
    with caplog.at_level(logging.WARNING):
        adapter = CustomerContactFactory(ApplicationSettings()).create()
    assert isinstance(adapter, MockPaytmCustomerContactAdapter)
    assert adapter.adapter_name == "mock"
    assert [record.getMessage() for record in caplog.records] == [
        MOCK_CUSTOMER_CONTACT_ACTIVE_WARNING
    ]
    assert "Mock" in MOCK_CUSTOMER_CONTACT_ACTIVE_WARNING


def test_contact_factory_in_paytm_mode_refuses_to_start_instead_of_a_synthetic_number(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Real customers must never get the synthetic number: no Mock fallback (ADR 0004)."""
    settings = ApplicationSettings(payment_gateway_mode=PaymentGatewayMode.PAYTM)
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(
            CustomerContactConfigurationError, match="PAYMENT_GATEWAY_MODE=paytm"
        ) as raised,
    ):
        CustomerContactFactory(settings).create()
    assert "Verify with Paytm" in str(raised.value)
    assert MOCK_CUSTOMER_CONTACT_ACTIVE_WARNING not in caplog.text


def test_mock_gives_the_same_synthetic_number_ending_42_for_every_sale() -> None:
    """C9 shows "ending 42"; the number is fictional (nine zeros between a 9 and 42)."""
    adapter = MockPaytmCustomerContactAdapter()
    assert adapter.find_customer_phone_number("sale-1") == SYNTHETIC_CUSTOMER_PHONE_NUMBER
    assert adapter.find_customer_phone_number("sale-2") == SYNTHETIC_CUSTOMER_PHONE_NUMBER
    assert SYNTHETIC_CUSTOMER_PHONE_NUMBER.national_number == "9000000042"
    assert SYNTHETIC_CUSTOMER_PHONE_NUMBER.last_two_digits == "42"
