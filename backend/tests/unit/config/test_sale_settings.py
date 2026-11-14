"""Settings for customer QR codes, sale expiry and the shop's calendar."""

import pytest
from pydantic import ValidationError

from emi_copilot.config.settings import ApplicationSettings
from tests.unit.config.test_settings import SETTINGS_ENVIRONMENT_VARIABLES


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removes settings variables a developer's shell or .env may have exported."""
    for variable_name in SETTINGS_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


def test_application_settings_without_environment_uses_documented_sale_defaults() -> None:
    """QR codes last 15 minutes, a choosing sale an hour, and days are counted in IST."""
    settings = ApplicationSettings()
    assert settings.customer_qr_signing_secret is None
    assert settings.customer_qr_token_lifetime_in_seconds == 900
    assert settings.customer_web_base_url == "http://localhost:5174"
    assert settings.sale_choosing_expiry_in_seconds == 3600
    assert settings.reporting_time_zone == "Asia/Kolkata"


def test_application_settings_reads_sale_values_and_hides_the_qr_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every sale setting is configurable; the signing secret never shows in repr."""
    synthetic_signing_key_text = (
        "synthetic-qr-signing-secret-0123456789"  # pragma: allowlist secret
    )
    monkeypatch.setenv("CUSTOMER_QR_SIGNING_SECRET", synthetic_signing_key_text)
    monkeypatch.setenv("CUSTOMER_QR_TOKEN_LIFETIME_IN_SECONDS", "600")
    monkeypatch.setenv("CUSTOMER_WEB_BASE_URL", "https://customer.example.test/shop/")
    monkeypatch.setenv("SALE_CHOOSING_EXPIRY_IN_SECONDS", "1800")
    monkeypatch.setenv("REPORTING_TIME_ZONE", "UTC")
    settings = ApplicationSettings()
    assert settings.customer_qr_signing_secret is not None
    assert settings.customer_qr_signing_secret.get_secret_value() == synthetic_signing_key_text
    assert synthetic_signing_key_text not in repr(settings)
    assert settings.customer_qr_token_lifetime_in_seconds == 600
    assert settings.customer_web_base_url == "https://customer.example.test/shop"
    assert settings.sale_choosing_expiry_in_seconds == 1800
    assert settings.reporting_time_zone == "UTC"


@pytest.mark.parametrize(
    ("variable_name", "unusable_value"),
    [
        ("CUSTOMER_QR_TOKEN_LIFETIME_IN_SECONDS", "59"),
        ("CUSTOMER_QR_TOKEN_LIFETIME_IN_SECONDS", "86401"),
        ("SALE_CHOOSING_EXPIRY_IN_SECONDS", "59"),
        ("CUSTOMER_WEB_BASE_URL", "ftp://customer.example.test"),
        ("CUSTOMER_WEB_BASE_URL", "customer.example.test"),
        ("CUSTOMER_WEB_BASE_URL", "https://customer.example.test/#t=old"),
        ("CUSTOMER_WEB_BASE_URL", "https://customer.example.test/?shop=1"),
        ("REPORTING_TIME_ZONE", "Asia/Chennai"),
        ("REPORTING_TIME_ZONE", "../etc/passwd"),
    ],
)
def test_application_settings_with_unusable_sale_value_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, unusable_value: str
) -> None:
    """Bad lifetimes, a base URL that is not a plain http(s) URL and unknown zones fail early."""
    monkeypatch.setenv(variable_name, unusable_value)
    with pytest.raises(ValidationError):
        ApplicationSettings()
