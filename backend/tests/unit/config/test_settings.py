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
    "MOCK_GATEWAY_WEBHOOK_SIGNING_SECRET",
    "PAYTM_MERCHANT_ID",
    "PAYTM_MERCHANT_KEY",
    "PAYTM_EMI_SUBVENTION_BASE_URL",
    "PAYTM_PAYMENT_LINK_BASE_URL",
    "PAYTM_TRANSACTION_STATUS_BASE_URL",
    "PAYTM_WEBHOOK_CALLBACK_URL",
    "MERCHANT_ACCESS_TOKEN_LIFETIME_IN_SECONDS",
    "MERCHANT_PAIRING_RATE_LIMIT_MAX_REQUESTS",
    "MERCHANT_PAIRING_RATE_LIMIT_WINDOW_IN_SECONDS",
    "CUSTOMER_QR_SIGNING_SECRET",
    "CUSTOMER_QR_TOKEN_LIFETIME_IN_SECONDS",
    "CUSTOMER_WEB_BASE_URL",
    "SALE_CHOOSING_EXPIRY_IN_SECONDS",
    "REPORTING_TIME_ZONE",
    "LOG_LEVEL",
)
SYNTHETIC_MERCHANT_ID = "SYNTHETICMID00000001"
SYNTHETIC_MERCHANT_KEY = "0123456789abcdef"  # pragma: allowlist secret
SYNTHETIC_MOCK_SIGNING_KEY = "synthetic-mock-signing-key-0123456789ab"  # pragma: allowlist secret


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


def test_application_settings_without_environment_has_no_gateway_secrets_or_base_urls() -> None:
    """No credential or secret exists by default; unset base URLs are filled by the factory."""
    settings = ApplicationSettings()
    assert settings.mock_gateway_webhook_signing_secret is None
    assert settings.paytm_merchant_id is None
    assert settings.paytm_merchant_key is None
    assert settings.paytm_webhook_callback_url is None
    assert settings.paytm_emi_subvention_base_url is None
    assert settings.paytm_payment_link_base_url is None
    assert settings.paytm_transaction_status_base_url is None


def test_application_settings_reads_and_hides_the_mock_webhook_signing_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Mock's webhook secret comes from the environment and never prints."""
    monkeypatch.setenv("MOCK_GATEWAY_WEBHOOK_SIGNING_SECRET", SYNTHETIC_MOCK_SIGNING_KEY)
    settings = ApplicationSettings()
    assert settings.mock_gateway_webhook_signing_secret is not None
    assert (
        settings.mock_gateway_webhook_signing_secret.get_secret_value()
        == SYNTHETIC_MOCK_SIGNING_KEY
    )
    assert SYNTHETIC_MOCK_SIGNING_KEY not in repr(settings)


def test_application_settings_reads_paytm_values_and_hides_the_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Paytm values come from the environment; the merchant id and key never print."""
    monkeypatch.setenv("PAYTM_MERCHANT_ID", SYNTHETIC_MERCHANT_ID)
    monkeypatch.setenv("PAYTM_MERCHANT_KEY", SYNTHETIC_MERCHANT_KEY)
    monkeypatch.setenv("PAYTM_PAYMENT_LINK_BASE_URL", "https://links.example.test")
    monkeypatch.setenv("PAYTM_WEBHOOK_CALLBACK_URL", "https://emi-copilot.example.test/webhooks")
    settings = ApplicationSettings()
    assert settings.paytm_merchant_id is not None
    assert settings.paytm_merchant_id.get_secret_value() == SYNTHETIC_MERCHANT_ID
    assert settings.paytm_merchant_key is not None
    assert settings.paytm_merchant_key.get_secret_value() == SYNTHETIC_MERCHANT_KEY
    assert settings.paytm_payment_link_base_url == "https://links.example.test"
    assert settings.paytm_webhook_callback_url == "https://emi-copilot.example.test/webhooks"
    assert SYNTHETIC_MERCHANT_ID not in repr(settings)
    assert SYNTHETIC_MERCHANT_KEY not in repr(settings)


@pytest.mark.parametrize(
    "variable_name",
    [
        "MOCK_GATEWAY_WEBHOOK_SIGNING_SECRET",
        "PAYTM_MERCHANT_ID",
        "PAYTM_MERCHANT_KEY",
        "PAYTM_EMI_SUBVENTION_BASE_URL",
        "PAYTM_PAYMENT_LINK_BASE_URL",
        "PAYTM_TRANSACTION_STATUS_BASE_URL",
        "PAYTM_WEBHOOK_CALLBACK_URL",
        "CUSTOMER_QR_SIGNING_SECRET",
    ],
)
def test_application_settings_reads_a_blank_gateway_value_as_not_set(
    monkeypatch: pytest.MonkeyPatch, variable_name: str
) -> None:
    """The empty placeholders copied from .env.example mean "not set", never an empty secret."""
    monkeypatch.setenv(variable_name, "  ")
    settings = ApplicationSettings()
    assert getattr(settings, variable_name.lower()) is None


def test_application_settings_without_environment_uses_documented_merchant_pairing_defaults() -> (
    None
):
    """A device token lasts 12 hours and pairing allows 10 requests a minute per client."""
    settings = ApplicationSettings()
    assert settings.merchant_access_token_lifetime_in_seconds == 43_200
    assert settings.merchant_pairing_rate_limit_max_requests == 10
    assert settings.merchant_pairing_rate_limit_window_in_seconds == 60


def test_application_settings_reads_merchant_pairing_values_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The token lifetime and the pairing rate limit are configurable."""
    monkeypatch.setenv("MERCHANT_ACCESS_TOKEN_LIFETIME_IN_SECONDS", "3600")
    monkeypatch.setenv("MERCHANT_PAIRING_RATE_LIMIT_MAX_REQUESTS", "3")
    monkeypatch.setenv("MERCHANT_PAIRING_RATE_LIMIT_WINDOW_IN_SECONDS", "300")
    settings = ApplicationSettings()
    assert settings.merchant_access_token_lifetime_in_seconds == 3600
    assert settings.merchant_pairing_rate_limit_max_requests == 3
    assert settings.merchant_pairing_rate_limit_window_in_seconds == 300


@pytest.mark.parametrize(
    ("variable_name", "unusable_value"),
    [
        ("MERCHANT_ACCESS_TOKEN_LIFETIME_IN_SECONDS", "59"),
        ("MERCHANT_ACCESS_TOKEN_LIFETIME_IN_SECONDS", "604801"),
        ("MERCHANT_PAIRING_RATE_LIMIT_MAX_REQUESTS", "0"),
        ("MERCHANT_PAIRING_RATE_LIMIT_WINDOW_IN_SECONDS", "0"),
    ],
)
def test_application_settings_with_unusable_merchant_pairing_value_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, unusable_value: str
) -> None:
    """A token shorter than a minute or longer than a week, or a zero limit, fails at startup."""
    monkeypatch.setenv(variable_name, unusable_value)
    with pytest.raises(ValidationError):
        ApplicationSettings()
