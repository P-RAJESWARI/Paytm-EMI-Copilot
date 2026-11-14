"""Settings for the live sale status stream, the payment rate limits and the Mock simulator."""

import pytest
from pydantic import ValidationError

from emi_copilot.config.settings import ApplicationSettings
from tests.unit.config.test_settings import SETTINGS_ENVIRONMENT_VARIABLES


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removes settings variables a developer's shell or .env may have exported."""
    for variable_name in SETTINGS_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


def test_application_settings_without_environment_uses_documented_live_feed_defaults() -> None:
    """A live stream holds 100 unread messages; a shop makes 60 payment calls a minute."""
    settings = ApplicationSettings()
    assert settings.sale_event_stream_maximum_queued_messages == 100
    assert settings.merchant_payment_rate_limit_max_requests == 60
    assert settings.merchant_payment_rate_limit_window_in_seconds == 60


def test_application_settings_reads_live_feed_values_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stream bound and the payment limits are configurable."""
    monkeypatch.setenv("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "5")
    monkeypatch.setenv("MERCHANT_PAYMENT_RATE_LIMIT_MAX_REQUESTS", "7")
    monkeypatch.setenv("MERCHANT_PAYMENT_RATE_LIMIT_WINDOW_IN_SECONDS", "30")
    settings = ApplicationSettings()
    assert settings.sale_event_stream_maximum_queued_messages == 5
    assert settings.merchant_payment_rate_limit_max_requests == 7
    assert settings.merchant_payment_rate_limit_window_in_seconds == 30


@pytest.mark.parametrize(
    ("variable_name", "unusable_value"),
    [
        ("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "0"),
        ("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "10001"),
        ("MERCHANT_PAYMENT_RATE_LIMIT_MAX_REQUESTS", "0"),
        ("MERCHANT_PAYMENT_RATE_LIMIT_WINDOW_IN_SECONDS", "0"),
    ],
)
def test_application_settings_with_unusable_live_feed_value_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, unusable_value: str
) -> None:
    """A bound outside its range fails at startup."""
    monkeypatch.setenv(variable_name, unusable_value)
    with pytest.raises(ValidationError):
        ApplicationSettings()
