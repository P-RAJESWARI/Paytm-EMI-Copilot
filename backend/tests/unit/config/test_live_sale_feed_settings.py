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
    """15 s heartbeats, 100 unread messages; 60 payment calls a shop, 600 webhooks a client."""
    settings = ApplicationSettings()
    assert settings.sale_event_stream_maximum_queued_messages == 100
    assert settings.sale_event_stream_heartbeat_interval_in_seconds == 15.0
    assert settings.merchant_payment_rate_limit_max_requests == 60
    assert settings.merchant_payment_rate_limit_window_in_seconds == 60
    assert settings.payment_webhook_rate_limit_max_requests == 600
    assert settings.payment_webhook_rate_limit_window_in_seconds == 60


def test_application_settings_reads_live_feed_values_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stream bound and the payment and webhook limits are configurable."""
    monkeypatch.setenv("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "5")
    monkeypatch.setenv("SALE_EVENT_STREAM_HEARTBEAT_INTERVAL_IN_SECONDS", "0.5")
    monkeypatch.setenv("MERCHANT_PAYMENT_RATE_LIMIT_MAX_REQUESTS", "7")
    monkeypatch.setenv("MERCHANT_PAYMENT_RATE_LIMIT_WINDOW_IN_SECONDS", "30")
    monkeypatch.setenv("PAYMENT_WEBHOOK_RATE_LIMIT_MAX_REQUESTS", "100")
    monkeypatch.setenv("PAYMENT_WEBHOOK_RATE_LIMIT_WINDOW_IN_SECONDS", "10")
    settings = ApplicationSettings()
    assert settings.sale_event_stream_maximum_queued_messages == 5
    assert settings.sale_event_stream_heartbeat_interval_in_seconds == 0.5
    assert settings.merchant_payment_rate_limit_max_requests == 7
    assert settings.merchant_payment_rate_limit_window_in_seconds == 30
    assert settings.payment_webhook_rate_limit_max_requests == 100
    assert settings.payment_webhook_rate_limit_window_in_seconds == 10


@pytest.mark.parametrize(
    ("variable_name", "unusable_value"),
    [
        ("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "0"),
        ("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "10001"),
        ("SALE_EVENT_STREAM_HEARTBEAT_INTERVAL_IN_SECONDS", "0"),
        ("SALE_EVENT_STREAM_HEARTBEAT_INTERVAL_IN_SECONDS", "301"),
        ("MERCHANT_PAYMENT_RATE_LIMIT_MAX_REQUESTS", "0"),
        ("MERCHANT_PAYMENT_RATE_LIMIT_WINDOW_IN_SECONDS", "0"),
        ("PAYMENT_WEBHOOK_RATE_LIMIT_MAX_REQUESTS", "0"),
        ("PAYMENT_WEBHOOK_RATE_LIMIT_WINDOW_IN_SECONDS", "0"),
    ],
)
def test_application_settings_with_unusable_live_feed_value_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, unusable_value: str
) -> None:
    """A bound outside its range fails at startup."""
    monkeypatch.setenv(variable_name, unusable_value)
    with pytest.raises(ValidationError):
        ApplicationSettings()
