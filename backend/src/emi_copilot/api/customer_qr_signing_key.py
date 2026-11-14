"""Turns CUSTOMER_QR_SIGNING_SECRET into the QR signing key once, at startup (composition root).

A missing secret in Mock gateway mode gets a random per-process key and a warning, because QR
codes signed with it stop working after a restart. Paytm mode is for real customers, so it
refuses to start without a configured secret instead of falling back (as ADR 0004 does for
gateway credentials).
"""

import logging
import secrets

from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
from emi_copilot.core.qr_token_signer import MINIMUM_SIGNING_KEY_LENGTH_IN_BYTES

customer_qr_signing_key_logger = logging.getLogger(__name__)

RANDOM_KEY_WARNING = (
    "CUSTOMER_QR_SIGNING_SECRET not configured; using a random per-process key, so customer QR "
    "codes stop working after a restart"
)
# Drawn once when this module is first imported, so every application built in one process
# (the tests build many) verifies the QR codes the others signed.
_PROCESS_CUSTOMER_QR_SIGNING_KEY = secrets.token_bytes(MINIMUM_SIGNING_KEY_LENGTH_IN_BYTES)


class CustomerQrSigningKeyConfigurationError(ValueError):
    """Raised at startup when the QR signing secret is missing in Paytm mode or too short.

    The message names the setting, never its value.
    """


def resolve_customer_qr_signing_key(settings: ApplicationSettings) -> bytes:
    """Gives the configured key, or the per-process one in Mock mode; otherwise fails startup."""
    configured_secret = settings.customer_qr_signing_secret
    if configured_secret is None:
        if settings.payment_gateway_mode is PaymentGatewayMode.PAYTM:
            raise CustomerQrSigningKeyConfigurationError(
                "PAYMENT_GATEWAY_MODE=paytm needs CUSTOMER_QR_SIGNING_SECRET; refusing to start."
            )
        customer_qr_signing_key_logger.warning(RANDOM_KEY_WARNING)
        return _PROCESS_CUSTOMER_QR_SIGNING_KEY
    secret_bytes = configured_secret.get_secret_value().encode("utf-8")
    if len(secret_bytes) < MINIMUM_SIGNING_KEY_LENGTH_IN_BYTES:
        raise CustomerQrSigningKeyConfigurationError(
            "CUSTOMER_QR_SIGNING_SECRET must be at least "
            f"{MINIMUM_SIGNING_KEY_LENGTH_IN_BYTES} bytes."
        )
    return secret_bytes
