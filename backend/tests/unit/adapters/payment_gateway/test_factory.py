"""Tests for PaymentGatewayFactory: Mock by default, Paytm only with complete credentials."""

import logging
import os

import pytest
from pydantic import SecretStr

from emi_copilot.adapters.payment_gateway.factory import (
    PAYTM_ACTIVE_MESSAGE,
    PaymentGatewayConfigurationError,
    PaymentGatewayFactory,
    build_paytm_gateway_configuration,
    build_paytm_http_clients,
)
from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.mock_webhook_signature import (
    MOCK_SIGNATURE_FIELD,
    calculate_mock_webhook_signature,
)
from emi_copilot.adapters.payment_gateway.paytm_adapter import PaytmPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    STAGING_EMI_SUBVENTION_BASE_URL,
    STAGING_PAYMENT_LINK_BASE_URL,
    STAGING_TRANSACTION_STATUS_BASE_URL,
)
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
from emi_copilot.domain.payments import GatewayPaymentStatus, UnverifiedWebhookNotification
from tests.contract.payment_gateway.paytm_fake_server import (
    SYNTHETIC_MERCHANT_ID,
    SYNTHETIC_MERCHANT_KEY,
)
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT

SYNTHETIC_SIGNING_KEY = "synthetic-mock-signing-key-0123456789ab"  # pragma: allowlist secret
GATEWAY_VARIABLE_PREFIXES = ("PAYMENT_GATEWAY_", "PAYTM_", "MOCK_GATEWAY_")


@pytest.fixture(autouse=True)
def clear_gateway_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removes gateway variables a developer's shell or .env may have exported."""
    for variable_name in list(os.environ):
        if variable_name.startswith(GATEWAY_VARIABLE_PREFIXES):
            monkeypatch.delenv(variable_name)


def _build_settings(**overrides: object) -> ApplicationSettings:
    """Builds settings from explicit values only, so no developer environment leaks in."""
    return ApplicationSettings.model_validate(overrides)


def _build_paytm_settings(**overrides: object) -> ApplicationSettings:
    """Builds Paytm-mode settings with the synthetic merchant id and key."""
    paytm_values: dict[str, object] = {
        "payment_gateway_mode": PaymentGatewayMode.PAYTM,
        "paytm_merchant_id": SYNTHETIC_MERCHANT_ID,
        "paytm_merchant_key": SYNTHETIC_MERCHANT_KEY,
    }
    return _build_settings(**(paytm_values | overrides))


def _create(settings: ApplicationSettings) -> PaymentGatewayPort:
    """Runs the factory with a fixed clock and predictable ids."""
    return PaymentGatewayFactory().create(settings, FixedClock(CREATED_AT), SequentialIdGenerator())


def _signed_mock_notification(secret: str) -> UnverifiedWebhookNotification:
    """Signs a Mock webhook with a given secret, the way a test client would."""
    signed_fields = {
        "orderId": "ORDER-SAMPLE-0001",
        "status": GatewayPaymentStatus.FAILED.value,
        "transactionId": "",
        "amountInPaise": "",
    }
    signature = calculate_mock_webhook_signature(signed_fields, secret.encode("utf-8"))
    return UnverifiedWebhookNotification({**signed_fields, MOCK_SIGNATURE_FIELD: signature})


def test_create_without_configuration_builds_the_mock_adapter() -> None:
    """The Mock is the default, so nobody can mistake local development for real payments."""
    payment_gateway = _create(_build_settings())
    assert isinstance(payment_gateway, MockPaymentGatewayAdapter)
    assert payment_gateway.adapter_name == "mock"


def test_create_mock_uses_the_configured_webhook_signing_secret() -> None:
    """A webhook signed with MOCK_GATEWAY_WEBHOOK_SIGNING_SECRET verifies on the built Mock."""
    payment_gateway = _create(
        _build_settings(mock_gateway_webhook_signing_secret=SYNTHETIC_SIGNING_KEY)
    )
    verified_event = payment_gateway.verify_webhook(
        _signed_mock_notification(SYNTHETIC_SIGNING_KEY)
    )
    assert verified_event.status is GatewayPaymentStatus.FAILED


def test_create_mock_without_secret_shares_one_random_secret_per_process(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Mocks built in one process accept each other's webhooks; the secret is never logged."""
    caplog.set_level(logging.INFO)
    first_mock = _create(_build_settings())
    second_mock = _create(_build_settings())
    assert isinstance(first_mock, MockPaymentGatewayAdapter)
    notification = first_mock.build_signed_notification(
        "ORDER-SAMPLE-0001", GatewayPaymentStatus.FAILED, None, None
    )
    assert second_mock.verify_webhook(notification).order_id == "ORDER-SAMPLE-0001"
    assert "per-process secret" in caplog.text


def test_create_mock_with_a_short_webhook_secret_raises_configuration_error() -> None:
    """A secret below 32 bytes would weaken the HMAC, so startup fails."""
    with pytest.raises(PaymentGatewayConfigurationError, match="at least 32 bytes"):
        _create(_build_settings(mock_gateway_webhook_signing_secret="x" * 31))


def test_create_paytm_with_full_credentials_builds_the_paytm_adapter_and_logs_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Paytm mode with an id and key builds the real adapter and announces it without secrets."""
    caplog.set_level(logging.INFO)
    payment_gateway = _create(_build_paytm_settings())
    assert isinstance(payment_gateway, PaytmPaymentGatewayAdapter)
    assert payment_gateway.adapter_name == "paytm"
    (active_record,) = [
        record for record in caplog.records if record.message == PAYTM_ACTIVE_MESSAGE
    ]
    assert active_record.levelno == logging.INFO
    assert active_record.__dict__["payment_gateway_adapter"] == "paytm"
    assert active_record.__dict__["payment_link_host"] == "securestage.paytmpayments.com"
    record_text = repr(active_record.__dict__)
    assert SYNTHETIC_MERCHANT_ID not in record_text
    assert SYNTHETIC_MERCHANT_KEY not in record_text


@pytest.mark.parametrize(
    ("missing_setting", "expected_variable_name"),
    [("paytm_merchant_id", "PAYTM_MERCHANT_ID"), ("paytm_merchant_key", "PAYTM_MERCHANT_KEY")],
)
def test_create_paytm_with_a_missing_credential_raises_and_never_falls_back_to_the_mock(
    missing_setting: str, expected_variable_name: str, caplog: pytest.LogCaptureFixture
) -> None:
    """ADR 0004: a missing merchant id or key fails startup; no Mock is built in its place."""
    caplog.set_level(logging.INFO)
    with pytest.raises(PaymentGatewayConfigurationError, match=expected_variable_name):
        _create(_build_paytm_settings(**{missing_setting: None}))
    assert "MockPaymentGatewayAdapter active" not in caplog.text


def test_create_paytm_with_a_key_of_unusable_length_raises_configuration_error() -> None:
    """The checksum needs a 16, 24 or 32 byte key; the error names the variable, not the key."""
    with pytest.raises(PaymentGatewayConfigurationError, match="PAYTM_MERCHANT_KEY") as raised:
        _create(_build_paytm_settings(paytm_merchant_key="short-key"))
    assert "short-key" not in str(raised.value)


def test_create_paytm_with_a_plain_http_base_url_raises_configuration_error() -> None:
    """A configured base URL that is not https fails startup instead of sending in clear text."""
    with pytest.raises(PaymentGatewayConfigurationError, match="https"):
        _create(_build_paytm_settings(paytm_payment_link_base_url="http://links.example.test"))


def test_build_paytm_gateway_configuration_fills_unset_base_urls_with_staging_hosts() -> None:
    """Unset base URLs become the staging hosts of paytm_api_definitions (ADR 0002, ADR 0011)."""
    configuration = build_paytm_gateway_configuration(_build_paytm_settings())
    assert configuration.emi_subvention_base_url == STAGING_EMI_SUBVENTION_BASE_URL
    assert configuration.payment_link_base_url == STAGING_PAYMENT_LINK_BASE_URL
    assert configuration.transaction_status_base_url == STAGING_TRANSACTION_STATUS_BASE_URL
    assert configuration.merchant_id == SecretStr(SYNTHETIC_MERCHANT_ID)
    assert configuration.webhook_callback_url is None


def test_build_paytm_gateway_configuration_keeps_explicit_base_urls() -> None:
    """Explicitly configured hosts, as production needs, are used as given."""
    configuration = build_paytm_gateway_configuration(
        _build_paytm_settings(
            paytm_emi_subvention_base_url="https://offers.example.test",
            paytm_payment_link_base_url="https://links.example.test",
            paytm_transaction_status_base_url="https://status.example.test",
            paytm_webhook_callback_url="https://emi-copilot.example.test/webhooks",
        )
    )
    assert configuration.emi_subvention_base_url == "https://offers.example.test"
    assert configuration.payment_link_base_url == "https://links.example.test"
    assert configuration.transaction_status_base_url == "https://status.example.test"
    assert configuration.webhook_callback_url == "https://emi-copilot.example.test/webhooks"


def test_build_paytm_http_clients_shares_one_client_per_host() -> None:
    """Families on one staging host share a client and breaker; the status host has its own."""
    settings = _build_paytm_settings()
    http_clients = build_paytm_http_clients(
        settings, build_paytm_gateway_configuration(settings), FixedClock(CREATED_AT)
    )
    assert http_clients.emi_subvention is http_clients.payment_link
    assert http_clients.transaction_status is not http_clients.payment_link
