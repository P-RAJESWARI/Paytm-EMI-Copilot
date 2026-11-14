"""Tests for typed application settings."""

import pytest
from pydantic import ValidationError

from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode

SETTINGS_ENVIRONMENT_VARIABLES = (
    "DATABASE_URL",
    "PAYMENT_GATEWAY_MODE",
    "PAYMENT_GATEWAY_CONNECT_TIMEOUT_IN_SECONDS",
    "PAYMENT_GATEWAY_READ_TIMEOUT_IN_SECONDS",
    "PAYMENT_GATEWAY_RETRY_MAX_ATTEMPTS",
    "PAYMENT_GATEWAY_RETRY_BASE_DELAY_IN_SECONDS",
    "PAYMENT_GATEWAY_RETRY_MAX_DELAY_IN_SECONDS",
    "PAYMENT_GATEWAY_CIRCUIT_BREAKER_FAILURE_THRESHOLD",
    "PAYMENT_GATEWAY_CIRCUIT_BREAKER_OPEN_DURATION_IN_SECONDS",
    "LOG_LEVEL",
)


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removes settings variables a developer's shell or .env may have exported."""
    for variable_name in SETTINGS_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


def test_application_settings_without_environment_defaults_payment_gateway_mode_to_mock() -> None:
    """The Mock gateway is the default so nobody believes real payments are live (ADR 0004)."""
    assert ApplicationSettings().payment_gateway_mode is PaymentGatewayMode.MOCK


def test_application_settings_reads_payment_gateway_mode_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PAYMENT_GATEWAY_MODE=paytm selects the real Paytm adapter mode."""
    monkeypatch.setenv("PAYMENT_GATEWAY_MODE", "paytm")
    assert ApplicationSettings().payment_gateway_mode is PaymentGatewayMode.PAYTM


def test_application_settings_with_unknown_payment_gateway_mode_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A typo in the gateway mode fails at startup instead of silently picking an adapter."""
    monkeypatch.setenv("PAYMENT_GATEWAY_MODE", "live")
    with pytest.raises(ValidationError):
        ApplicationSettings()


def test_application_settings_with_non_positive_timeout_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gateway timeouts must be positive so an external call can never wait forever."""
    monkeypatch.setenv("PAYMENT_GATEWAY_READ_TIMEOUT_IN_SECONDS", "0")
    with pytest.raises(ValidationError):
        ApplicationSettings()


def test_application_settings_hides_database_url_from_its_representation() -> None:
    """The database URL carries a password, so printing settings must not reveal it."""
    settings = ApplicationSettings()
    assert "emi_copilot_local_only" not in repr(settings)
    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg://")


def test_application_settings_without_environment_uses_documented_resilience_defaults() -> None:
    """Three attempts for reads, and the breaker opens after five failures for thirty seconds."""
    settings = ApplicationSettings()
    assert settings.payment_gateway_retry_max_attempts == 3
    assert settings.payment_gateway_retry_base_delay_in_seconds == 0.2
    assert settings.payment_gateway_retry_max_delay_in_seconds == 2.0
    assert settings.payment_gateway_circuit_breaker_failure_threshold == 5
    assert settings.payment_gateway_circuit_breaker_open_duration_in_seconds == 30.0


def test_application_settings_reads_resilience_values_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every retry and breaker value can be tuned per environment."""
    monkeypatch.setenv("PAYMENT_GATEWAY_RETRY_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("PAYMENT_GATEWAY_CIRCUIT_BREAKER_OPEN_DURATION_IN_SECONDS", "60")
    settings = ApplicationSettings()
    assert settings.payment_gateway_retry_max_attempts == 4
    assert settings.payment_gateway_circuit_breaker_open_duration_in_seconds == 60.0


@pytest.mark.parametrize(
    ("variable_name", "unusable_value"),
    [
        ("PAYMENT_GATEWAY_RETRY_MAX_ATTEMPTS", "0"),
        ("PAYMENT_GATEWAY_RETRY_MAX_ATTEMPTS", "11"),
        ("PAYMENT_GATEWAY_RETRY_BASE_DELAY_IN_SECONDS", "0"),
        ("PAYMENT_GATEWAY_RETRY_MAX_DELAY_IN_SECONDS", "-1"),
        ("PAYMENT_GATEWAY_RETRY_BASE_DELAY_IN_SECONDS", "5"),
        ("PAYMENT_GATEWAY_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "0"),
        ("PAYMENT_GATEWAY_CIRCUIT_BREAKER_OPEN_DURATION_IN_SECONDS", "0"),
    ],
)
def test_application_settings_with_unusable_resilience_value_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, unusable_value: str
) -> None:
    """No retries without bound, no zero delays, base delay within max, a breaker that can open."""
    monkeypatch.setenv(variable_name, unusable_value)
    with pytest.raises(ValidationError):
        ApplicationSettings()
