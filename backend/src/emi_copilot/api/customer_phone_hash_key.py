"""Turns CUSTOMER_PHONE_HASH_SECRET into the customer hash key once, at startup (composition root).

A missing secret in Mock gateway mode gets a random per-process key and a warning, because phone
hashes made with it no longer match after a restart and codes in flight stop working. Paytm mode
is for real customers, so it refuses to start without a configured secret instead of falling
back, as resolve_customer_qr_signing_key does for the QR secret.
"""

import logging
import secrets

from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
from emi_copilot.core.keyed_hasher import MINIMUM_HASH_KEY_LENGTH_IN_BYTES

customer_phone_hash_key_logger = logging.getLogger(__name__)

RANDOM_PHONE_HASH_KEY_WARNING = (
    "CUSTOMER_PHONE_HASH_SECRET not configured; using a random per-process key, so customer "
    "phone hashes change and open one-time codes stop working after a restart"
)
# Drawn once when this module is first imported, so every application built in one process
# (the tests build many) hashes alike.
_PROCESS_CUSTOMER_PHONE_HASH_KEY = secrets.token_bytes(MINIMUM_HASH_KEY_LENGTH_IN_BYTES)


class CustomerPhoneHashKeyConfigurationError(ValueError):
    """Raised at startup when the hash secret is missing in Paytm mode or too short.

    The message names the setting, never its value.
    """


def resolve_customer_phone_hash_key(settings: ApplicationSettings) -> bytes:
    """Gives the configured key, or the per-process one in Mock mode; otherwise fails startup."""
    configured_secret = settings.customer_phone_hash_secret
    if configured_secret is None:
        if settings.payment_gateway_mode is PaymentGatewayMode.PAYTM:
            raise CustomerPhoneHashKeyConfigurationError(
                "PAYMENT_GATEWAY_MODE=paytm needs CUSTOMER_PHONE_HASH_SECRET; refusing to start."
            )
        customer_phone_hash_key_logger.warning(RANDOM_PHONE_HASH_KEY_WARNING)
        return _PROCESS_CUSTOMER_PHONE_HASH_KEY
    secret_bytes = configured_secret.get_secret_value().encode("utf-8")
    if len(secret_bytes) < MINIMUM_HASH_KEY_LENGTH_IN_BYTES:
        raise CustomerPhoneHashKeyConfigurationError(
            f"CUSTOMER_PHONE_HASH_SECRET must be at least {MINIMUM_HASH_KEY_LENGTH_IN_BYTES} bytes."
        )
    return secret_bytes
