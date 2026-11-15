"""The customer hash key: configured, per-process in Mock mode with a warning, refused in Paytm."""

import logging

import pytest
from pydantic import SecretStr

from emi_copilot.api.customer_phone_hash_key import (
    RANDOM_PHONE_HASH_KEY_WARNING,
    CustomerPhoneHashKeyConfigurationError,
    resolve_customer_phone_hash_key,
)
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode

SYNTHETIC_HASH_KEY_TEXT = "synthetic-customer-hash-secret-0123456789"  # pragma: allowlist secret


def test_configured_secret_becomes_the_hash_key() -> None:
    """The secret's UTF-8 bytes are the HMAC key."""
    settings = ApplicationSettings(customer_phone_hash_secret=SecretStr(SYNTHETIC_HASH_KEY_TEXT))
    assert resolve_customer_phone_hash_key(settings) == SYNTHETIC_HASH_KEY_TEXT.encode("utf-8")


def test_missing_secret_in_mock_mode_gives_one_per_process_key_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Every application in the process shares the drawn key; the log says hashes won't last."""
    with caplog.at_level(logging.WARNING):
        first_key = resolve_customer_phone_hash_key(ApplicationSettings())
        second_key = resolve_customer_phone_hash_key(ApplicationSettings())
    assert first_key == second_key
    assert len(first_key) >= 32
    assert RANDOM_PHONE_HASH_KEY_WARNING in caplog.text


def test_missing_secret_in_paytm_mode_refuses_to_start() -> None:
    """Real customers' phone hashes must survive a restart, or the service does not start."""
    settings = ApplicationSettings(payment_gateway_mode=PaymentGatewayMode.PAYTM)
    with pytest.raises(CustomerPhoneHashKeyConfigurationError, match="CUSTOMER_PHONE_HASH_SECRET"):
        resolve_customer_phone_hash_key(settings)


def test_short_secret_is_refused_without_echoing_it() -> None:
    """A short key makes phone hashes easier to reverse; the message names only the setting."""
    settings = ApplicationSettings(customer_phone_hash_secret=SecretStr("too-short"))
    with pytest.raises(CustomerPhoneHashKeyConfigurationError) as raised_error:
        resolve_customer_phone_hash_key(settings)
    assert "too-short" not in str(raised_error.value)
