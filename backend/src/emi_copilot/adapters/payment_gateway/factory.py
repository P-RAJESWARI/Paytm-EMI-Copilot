"""PaymentGatewayFactory: the one place that turns configuration into a payment gateway adapter.

Only the composition root (api/dependencies.py) imports this module (ADR 0008); services see
the PaymentGatewayPort it returns and never a concrete adapter.
"""

import logging
import random
import secrets
import time
from datetime import timedelta
from urllib.parse import urlsplit

from pydantic import SecretStr

from emi_copilot.adapters.payment_gateway.checksum_signer import PaytmChecksumSigner
from emi_copilot.adapters.payment_gateway.mock_adapter import (
    MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES,
    MockPaymentGatewayAdapter,
)
from emi_copilot.adapters.payment_gateway.paytm_adapter import PaytmPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    ADAPTER_NAME,
    STAGING_EMI_SUBVENTION_BASE_URL,
    STAGING_PAYMENT_LINK_BASE_URL,
    STAGING_TRANSACTION_STATUS_BASE_URL,
)
from emi_copilot.adapters.payment_gateway.paytm_gateway_configuration import (
    PaytmGatewayConfiguration,
    PaytmHttpClients,
)
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
from emi_copilot.core.circuit_breaker import CircuitBreaker
from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.resilient_http_client import (
    ResilientHttpClient,
    RetryPolicy,
    UpstreamTimeouts,
    build_upstream_http_client,
)

payment_gateway_factory_logger = logging.getLogger(__name__)

PAYTM_ACTIVE_MESSAGE = "PaytmPaymentGatewayAdapter active: real payment gateway calls are made"
# Drawn once when this module is first imported, so every Mock built in one process shares it.
_PROCESS_MOCK_WEBHOOK_SIGNING_SECRET = secrets.token_bytes(
    MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES
)


class PaymentGatewayConfigurationError(ValueError):
    """Raised at startup when the configured gateway mode cannot be built as configured.

    The message names the missing or unusable setting, never its value (ADR 0004).
    """


def resolve_mock_webhook_signing_secret(settings: ApplicationSettings) -> bytes:
    """Gives the configured Mock webhook secret, or the per-process one when none is set."""
    configured_secret = settings.mock_gateway_webhook_signing_secret
    if configured_secret is None:
        payment_gateway_factory_logger.info(
            "mock webhook signing secret not configured; using a random per-process secret"
        )
        return _PROCESS_MOCK_WEBHOOK_SIGNING_SECRET
    secret_bytes = configured_secret.get_secret_value().encode("utf-8")
    if len(secret_bytes) < MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES:
        raise PaymentGatewayConfigurationError(
            "MOCK_GATEWAY_WEBHOOK_SIGNING_SECRET must be at least "
            f"{MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES} bytes."
        )
    return secret_bytes


def _require_credential(value: SecretStr | None, variable_name: str) -> SecretStr:
    """Returns a configured credential or fails startup naming the variable, never falling back."""
    if value is None:
        raise PaymentGatewayConfigurationError(
            f"PAYMENT_GATEWAY_MODE=paytm needs {variable_name}; refusing to start (ADR 0004)."
        )
    return value


def build_paytm_gateway_configuration(settings: ApplicationSettings) -> PaytmGatewayConfiguration:
    """Builds the Paytm configuration, filling each unset base URL with its staging host."""
    merchant_id = _require_credential(settings.paytm_merchant_id, "PAYTM_MERCHANT_ID")
    merchant_key = _require_credential(settings.paytm_merchant_key, "PAYTM_MERCHANT_KEY")
    try:
        return PaytmGatewayConfiguration(
            merchant_id=merchant_id,
            merchant_key=merchant_key,
            emi_subvention_base_url=(
                settings.paytm_emi_subvention_base_url or STAGING_EMI_SUBVENTION_BASE_URL
            ),
            payment_link_base_url=(
                settings.paytm_payment_link_base_url or STAGING_PAYMENT_LINK_BASE_URL
            ),
            transaction_status_base_url=(
                settings.paytm_transaction_status_base_url or STAGING_TRANSACTION_STATUS_BASE_URL
            ),
            webhook_callback_url=settings.paytm_webhook_callback_url,
        )
    except ValueError as invalid_value_error:
        raise PaymentGatewayConfigurationError(
            f"The Paytm configuration is unusable: {invalid_value_error}"
        ) from invalid_value_error


def _build_resilient_client(
    settings: ApplicationSettings, host: str, clock: Clock
) -> ResilientHttpClient:
    """Builds one breaker-guarded client for one Paytm host with the configured timeouts."""
    timeouts = UpstreamTimeouts(
        connect_timeout_in_seconds=settings.payment_gateway_connect_timeout_in_seconds,
        read_timeout_in_seconds=settings.payment_gateway_read_timeout_in_seconds,
        write_timeout_in_seconds=settings.payment_gateway_read_timeout_in_seconds,
        pool_timeout_in_seconds=settings.payment_gateway_connect_timeout_in_seconds,
    )
    circuit_breaker = CircuitBreaker(
        dependency_name=f"{ADAPTER_NAME}:{host}",
        failure_threshold=settings.payment_gateway_circuit_breaker_failure_threshold,
        open_duration=timedelta(
            seconds=settings.payment_gateway_circuit_breaker_open_duration_in_seconds
        ),
        clock=clock,
    )
    return ResilientHttpClient(
        http_client=build_upstream_http_client(timeouts),
        retry_policy=RetryPolicy(
            max_attempts=settings.payment_gateway_retry_max_attempts,
            base_delay_in_seconds=settings.payment_gateway_retry_base_delay_in_seconds,
            max_delay_in_seconds=settings.payment_gateway_retry_max_delay_in_seconds,
        ),
        circuit_breaker=circuit_breaker,
        sleep=time.sleep,
        random_source=random.SystemRandom(),
    )


def build_paytm_http_clients(
    settings: ApplicationSettings, configuration: PaytmGatewayConfiguration, clock: Clock
) -> PaytmHttpClients:
    """Builds one client and breaker per distinct host, so one failing host trips one breaker."""
    clients_by_host: dict[str, ResilientHttpClient] = {}

    def client_for(base_url: str) -> ResilientHttpClient:
        """Gives the shared client of the URL's host, building it on first use."""
        host = urlsplit(base_url).netloc
        if host not in clients_by_host:
            clients_by_host[host] = _build_resilient_client(settings, host, clock)
        return clients_by_host[host]

    return PaytmHttpClients(
        emi_subvention=client_for(configuration.emi_subvention_base_url),
        payment_link=client_for(configuration.payment_link_base_url),
        transaction_status=client_for(configuration.transaction_status_base_url),
    )


def _log_paytm_adapter_active(configuration: PaytmGatewayConfiguration) -> None:
    """Announces the real adapter and its hosts; never the merchant id, key or a query string."""
    payment_gateway_factory_logger.info(
        PAYTM_ACTIVE_MESSAGE,
        extra={
            "payment_gateway_adapter": ADAPTER_NAME,
            "emi_subvention_host": urlsplit(configuration.emi_subvention_base_url).netloc,
            "payment_link_host": urlsplit(configuration.payment_link_base_url).netloc,
            "transaction_status_host": urlsplit(configuration.transaction_status_base_url).netloc,
            "has_webhook_callback_url": configuration.webhook_callback_url is not None,
        },
    )


# Pattern: Factory. Chooses the Mock or the real Paytm adapter from configuration in one place,
# and refuses to start Paytm mode without credentials instead of falling back (ADR 0004).
class PaymentGatewayFactory:
    """Builds the PaymentGatewayPort for PAYMENT_GATEWAY_MODE; the Mock is the default."""

    def create(
        self, settings: ApplicationSettings, clock: Clock, id_generator: IdGenerator
    ) -> PaymentGatewayPort:
        """Builds the configured adapter; the Mock warns on its own, Paytm is logged here."""
        if settings.payment_gateway_mode is PaymentGatewayMode.PAYTM:
            return self._create_paytm_adapter(settings, clock, id_generator)
        return MockPaymentGatewayAdapter(clock, resolve_mock_webhook_signing_secret(settings))

    def _create_paytm_adapter(
        self, settings: ApplicationSettings, clock: Clock, id_generator: IdGenerator
    ) -> PaytmPaymentGatewayAdapter:
        """Builds the Paytm adapter from complete credentials, or raises a configuration error."""
        configuration = build_paytm_gateway_configuration(settings)
        try:
            checksum_signer = PaytmChecksumSigner(configuration.merchant_key)
        except ValueError as invalid_key_error:
            raise PaymentGatewayConfigurationError(
                "PAYTM_MERCHANT_KEY must be 16, 24 or 32 bytes long."
            ) from invalid_key_error
        adapter = PaytmPaymentGatewayAdapter(
            configuration=configuration,
            http_clients=build_paytm_http_clients(settings, configuration, clock),
            checksum_signer=checksum_signer,
            clock=clock,
            id_generator=id_generator,
        )
        _log_paytm_adapter_active(configuration)
        return adapter
