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
    """A live stream holds at most 100 unread messages by default."""
    assert ApplicationSettings().sale_event_stream_maximum_queued_messages == 100


def test_application_settings_reads_live_feed_values_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stream bound is configurable."""
    monkeypatch.setenv("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "5")
    assert ApplicationSettings().sale_event_stream_maximum_queued_messages == 5


@pytest.mark.parametrize(
    ("variable_name", "unusable_value"),
    [
        ("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "0"),
        ("SALE_EVENT_STREAM_MAXIMUM_QUEUED_MESSAGES", "10001"),
    ],
)
def test_application_settings_with_unusable_live_feed_value_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, unusable_value: str
) -> None:
    """A bound outside its range fails at startup."""
    monkeypatch.setenv(variable_name, unusable_value)
    with pytest.raises(ValidationError):
        ApplicationSettings()
