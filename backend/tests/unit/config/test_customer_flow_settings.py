"""Settings for customer sessions, consent one-time codes and the customer hash secret."""

import pytest
from pydantic import ValidationError

from emi_copilot.config.settings import ApplicationSettings, MockFinancialProfileChoice
from tests.unit.config.test_settings import SETTINGS_ENVIRONMENT_VARIABLES

SYNTHETIC_HASH_KEY_TEXT = "synthetic-customer-hash-secret-0123456789"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removes settings variables a developer's shell or .env may have exported."""
    for variable_name in SETTINGS_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


def test_defaults_are_the_adr_0022_demo_values() -> None:
    """30-minute sessions; codes allow 3 attempts, last 5 minutes and resend after 30 seconds."""
    settings = ApplicationSettings()
    assert settings.customer_session_lifetime_in_seconds == 1800
    assert settings.consent_otp_lifetime_in_seconds == 300
    assert settings.consent_otp_maximum_attempts == 3
    assert settings.consent_otp_resend_wait_in_seconds == 30
    assert settings.mock_consent_otp_code.get_secret_value() == "123456"
    assert settings.customer_phone_hash_secret is None


def test_values_are_read_from_the_environment_and_secrets_stay_out_of_repr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every value is configurable; neither the demo code nor the hash secret shows in repr."""
    monkeypatch.setenv("CUSTOMER_SESSION_LIFETIME_IN_SECONDS", "900")
    monkeypatch.setenv("CONSENT_OTP_LIFETIME_IN_SECONDS", "120")
    monkeypatch.setenv("CONSENT_OTP_MAXIMUM_ATTEMPTS", "5")
    monkeypatch.setenv("CONSENT_OTP_RESEND_WAIT_IN_SECONDS", "10")
    monkeypatch.setenv("MOCK_CONSENT_OTP_CODE", "004242")
    monkeypatch.setenv("CUSTOMER_PHONE_HASH_SECRET", SYNTHETIC_HASH_KEY_TEXT)
    settings = ApplicationSettings()
    assert settings.customer_session_lifetime_in_seconds == 900
    assert settings.consent_otp_lifetime_in_seconds == 120
    assert settings.consent_otp_maximum_attempts == 5
    assert settings.consent_otp_resend_wait_in_seconds == 10
    assert settings.mock_consent_otp_code.get_secret_value() == "004242"
    assert settings.customer_phone_hash_secret is not None
    assert settings.customer_phone_hash_secret.get_secret_value() == SYNTHETIC_HASH_KEY_TEXT
    assert "004242" not in repr(settings)
    assert SYNTHETIC_HASH_KEY_TEXT not in repr(settings)


def test_customer_rate_limits_default_to_the_documented_demo_values() -> None:
    """20 QR exchanges a minute per address; 5 code requests and 10 consents per 10 minutes."""
    settings = ApplicationSettings()
    assert settings.customer_session_start_rate_limit_max_requests == 20
    assert settings.customer_session_start_rate_limit_window_in_seconds == 60
    assert settings.consent_otp_request_rate_limit_max_requests == 5
    assert settings.consent_otp_request_rate_limit_window_in_seconds == 600
    assert settings.customer_consent_rate_limit_max_requests == 10
    assert settings.customer_consent_rate_limit_window_in_seconds == 600


@pytest.mark.parametrize(
    "variable_name",
    [
        "CUSTOMER_SESSION_START_RATE_LIMIT_MAX_REQUESTS",
        "CUSTOMER_SESSION_START_RATE_LIMIT_WINDOW_IN_SECONDS",
        "CONSENT_OTP_REQUEST_RATE_LIMIT_MAX_REQUESTS",
        "CONSENT_OTP_REQUEST_RATE_LIMIT_WINDOW_IN_SECONDS",
        "CUSTOMER_CONSENT_RATE_LIMIT_MAX_REQUESTS",
        "CUSTOMER_CONSENT_RATE_LIMIT_WINDOW_IN_SECONDS",
    ],
)
def test_customer_rate_limits_refuse_zero(
    monkeypatch: pytest.MonkeyPatch, variable_name: str
) -> None:
    """A limit or window of zero would refuse every customer, so it fails at startup."""
    monkeypatch.setenv(variable_name, "0")
    with pytest.raises(ValidationError, match=f"(?i){variable_name}"):
        ApplicationSettings()


def test_a_blank_hash_secret_copied_from_env_example_means_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The empty placeholder is not an empty key."""
    monkeypatch.setenv("CUSTOMER_PHONE_HASH_SECRET", "  ")
    assert ApplicationSettings().customer_phone_hash_secret is None


@pytest.mark.parametrize(
    ("variable_name", "unusable_value"),
    [
        ("CUSTOMER_SESSION_LIFETIME_IN_SECONDS", "59"),
        ("CUSTOMER_SESSION_LIFETIME_IN_SECONDS", "86401"),
        ("CONSENT_OTP_LIFETIME_IN_SECONDS", "29"),
        ("CONSENT_OTP_MAXIMUM_ATTEMPTS", "0"),
        ("CONSENT_OTP_MAXIMUM_ATTEMPTS", "11"),
        ("CONSENT_OTP_RESEND_WAIT_IN_SECONDS", "0"),
        ("CONSENT_OTP_RESEND_WAIT_IN_SECONDS", "300"),
        ("MOCK_CONSENT_OTP_CODE", "12345"),
        ("MOCK_CONSENT_OTP_CODE", "12345a"),
    ],
)
def test_unusable_values_are_refused_at_startup(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, unusable_value: str
) -> None:
    """A resend wait as long as the code's life, or a code that is not six digits, fails fast."""
    monkeypatch.setenv(variable_name, unusable_value)
    with pytest.raises(ValidationError, match=f"(?i){variable_name}"):
        ApplicationSettings()


def test_mock_financial_profile_is_standard_unless_the_demo_asks_for_risky(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MOCK_FINANCIAL_PROFILE picks the synthetic design customer; standard is the default."""
    assert ApplicationSettings().mock_financial_profile is MockFinancialProfileChoice.STANDARD
    monkeypatch.setenv("MOCK_FINANCIAL_PROFILE", "risky")
    assert ApplicationSettings().mock_financial_profile is MockFinancialProfileChoice.RISKY


def test_unknown_mock_financial_profile_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """A typo fails at startup instead of silently showing another customer's bands."""
    monkeypatch.setenv("MOCK_FINANCIAL_PROFILE", "comfortable")
    with pytest.raises(ValidationError, match="mock_financial_profile"):
        ApplicationSettings()
