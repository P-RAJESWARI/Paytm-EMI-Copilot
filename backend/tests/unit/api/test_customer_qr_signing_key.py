"""The QR signing key: configured, per-process in Mock mode (with a warning), refused in Paytm."""

import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from emi_copilot.api.customer_qr_signing_key import (
    RANDOM_KEY_WARNING,
    CustomerQrSigningKeyConfigurationError,
    resolve_customer_qr_signing_key,
)
from emi_copilot.api.dependencies import ApplicationComponents
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
from emi_copilot.core.session_code_generator import RandomSessionCodeGenerator
from emi_copilot.main import create_application

SYNTHETIC_SIGNING_KEY_TEXT = "synthetic-qr-signing-secret-0123456789"  # pragma: allowlist secret


def test_configured_secret_becomes_the_signing_key() -> None:
    """The secret's UTF-8 bytes are the HMAC key."""
    settings = ApplicationSettings(customer_qr_signing_secret=SecretStr(SYNTHETIC_SIGNING_KEY_TEXT))
    assert resolve_customer_qr_signing_key(settings) == SYNTHETIC_SIGNING_KEY_TEXT.encode("utf-8")


def test_missing_secret_in_mock_mode_gives_one_per_process_key_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Every application in the process shares the drawn key; the log says QR codes won't last."""
    with caplog.at_level(logging.WARNING):
        first_key = resolve_customer_qr_signing_key(ApplicationSettings())
        second_key = resolve_customer_qr_signing_key(ApplicationSettings())
    assert first_key == second_key
    assert len(first_key) >= 32
    assert RANDOM_KEY_WARNING in caplog.text


def test_missing_secret_in_paytm_mode_refuses_to_start() -> None:
    """Real customers get QR codes that survive a restart, or the service does not start."""
    settings = ApplicationSettings(payment_gateway_mode=PaymentGatewayMode.PAYTM)
    with pytest.raises(CustomerQrSigningKeyConfigurationError, match="CUSTOMER_QR_SIGNING_SECRET"):
        resolve_customer_qr_signing_key(settings)


def test_short_secret_is_refused_without_echoing_it() -> None:
    """A short HMAC key makes QR codes easier to forge; the message names only the setting."""
    settings = ApplicationSettings(customer_qr_signing_secret=SecretStr("too-short"))
    with pytest.raises(CustomerQrSigningKeyConfigurationError) as raised_error:
        resolve_customer_qr_signing_key(settings)
    assert "too-short" not in str(raised_error.value)


def test_startup_keeps_the_key_and_a_random_session_code_generator_on_the_components() -> None:
    """Both outlive one request; the key never shows in the components' repr."""
    application = create_application(
        ApplicationSettings(customer_qr_signing_secret=SecretStr(SYNTHETIC_SIGNING_KEY_TEXT))
    )
    with TestClient(application):
        components: ApplicationComponents = application.state.application_components
        assert components.customer_qr_signing_key == SYNTHETIC_SIGNING_KEY_TEXT.encode("utf-8")
        assert isinstance(components.session_code_generator, RandomSessionCodeGenerator)
        assert SYNTHETIC_SIGNING_KEY_TEXT not in repr(components)
