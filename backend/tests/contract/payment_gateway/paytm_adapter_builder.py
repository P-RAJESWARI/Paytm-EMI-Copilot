"""Wires the real Paytm adapter to a FakePaytmServer through httpx.MockTransport; no network."""

import random
from dataclasses import dataclass
from datetime import timedelta

import httpx
from pydantic import SecretStr

from emi_copilot.adapters.payment_gateway.checksum_signer import (
    ChecksumSaltSource,
    PaytmChecksumSigner,
)
from emi_copilot.adapters.payment_gateway.paytm_adapter import PaytmPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    STAGING_EMI_SUBVENTION_BASE_URL,
    STAGING_PAYMENT_LINK_BASE_URL,
    STAGING_TRANSACTION_STATUS_BASE_URL,
)
from emi_copilot.adapters.payment_gateway.paytm_gateway_configuration import (
    PaytmGatewayConfiguration,
    PaytmHttpClients,
)
from emi_copilot.core.circuit_breaker import CircuitBreaker
from emi_copilot.core.resilient_http_client import ResilientHttpClient, RetryPolicy
from tests.contract.payment_gateway.paytm_fake_server import (
    SYNTHETIC_MERCHANT_ID,
    SYNTHETIC_MERCHANT_KEY,
    FakePaytmServer,
)
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT

SYNTHETIC_WEBHOOK_CALLBACK_URL = "https://emi-copilot.example.test/api/v1/webhooks/paytm"
RANDOM_SEED = 20261114


class CountingIdGenerator:
    """IdGenerator giving REQUEST0000...1, REQUEST0000...2: 32 characters, Paytm's maximum."""

    def __init__(self) -> None:
        """Starts counting at zero."""
        self._issued_count = 0

    def new_id(self) -> str:
        """Returns the next numbered request id."""
        self._issued_count += 1
        return f"REQUEST{self._issued_count:025d}"


def build_synthetic_configuration(
    webhook_callback_url: str | None = SYNTHETIC_WEBHOOK_CALLBACK_URL,
) -> PaytmGatewayConfiguration:
    """Builds a configuration with the synthetic merchant id and key and the staging hosts."""
    return PaytmGatewayConfiguration(
        merchant_id=SecretStr(SYNTHETIC_MERCHANT_ID),
        merchant_key=SecretStr(SYNTHETIC_MERCHANT_KEY),
        emi_subvention_base_url=STAGING_EMI_SUBVENTION_BASE_URL,
        payment_link_base_url=STAGING_PAYMENT_LINK_BASE_URL,
        transaction_status_base_url=STAGING_TRANSACTION_STATUS_BASE_URL,
        webhook_callback_url=webhook_callback_url,
    )


@dataclass
class PaytmAdapterUnderTest:
    """The adapter, its fake server, its one resilient client and breaker, and recorded sleeps."""

    adapter: PaytmPaymentGatewayAdapter
    server: FakePaytmServer
    resilient_client: ResilientHttpClient
    circuit_breaker: CircuitBreaker
    recorded_sleep_delays: list[float]


def build_paytm_adapter_under_test(
    *,
    max_attempts: int = 3,
    failure_threshold: int = 5,
    salt_source: ChecksumSaltSource | None = None,
    webhook_callback_url: str | None = SYNTHETIC_WEBHOOK_CALLBACK_URL,
) -> PaytmAdapterUnderTest:
    """Builds the adapter on one breaker-guarded client whose transport is a fresh fake Paytm."""
    server = FakePaytmServer()
    clock = FixedClock(CREATED_AT)
    circuit_breaker = CircuitBreaker(
        dependency_name="paytm",
        failure_threshold=failure_threshold,
        open_duration=timedelta(seconds=30),
        clock=clock,
    )
    recorded_sleep_delays: list[float] = []
    resilient_client = ResilientHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(server.handle_request)),
        retry_policy=RetryPolicy(
            max_attempts=max_attempts, base_delay_in_seconds=0.1, max_delay_in_seconds=0.3
        ),
        circuit_breaker=circuit_breaker,
        sleep=recorded_sleep_delays.append,
        random_source=random.Random(RANDOM_SEED),  # noqa: S311 - seeded jitter, not security
    )
    adapter = PaytmPaymentGatewayAdapter(
        configuration=build_synthetic_configuration(webhook_callback_url),
        http_clients=PaytmHttpClients(resilient_client, resilient_client, resilient_client),
        checksum_signer=PaytmChecksumSigner(SecretStr(SYNTHETIC_MERCHANT_KEY), salt_source),
        clock=clock,
        id_generator=CountingIdGenerator(),
    )
    return PaytmAdapterUnderTest(
        adapter, server, resilient_client, circuit_breaker, recorded_sleep_delays
    )
