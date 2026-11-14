"""Typed application settings read from environment variables."""

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    STAGING_EMI_SUBVENTION_BASE_URL,
    STAGING_PAYMENT_LINK_BASE_URL,
    STAGING_TRANSACTION_STATUS_BASE_URL,
)

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Local-only default that matches docker-compose.yml. Never a real credential.
LOCAL_DEVELOPMENT_DATABASE_URL = (
    # pragma: allowlist nextline secret
    "postgresql+psycopg://emi_copilot:emi_copilot_local_only@localhost:55432/emi_copilot"
)


class PaymentGatewayMode(StrEnum):
    """Which payment gateway adapter the factory builds (ADR 0004)."""

    MOCK = "mock"
    PAYTM = "paytm"


class ApplicationSettings(BaseSettings):
    """All runtime configuration, one typed field per environment variable."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore", frozen=True)

    database_url: SecretStr = Field(default=SecretStr(LOCAL_DEVELOPMENT_DATABASE_URL))
    payment_gateway_mode: PaymentGatewayMode = PaymentGatewayMode.MOCK
    payment_gateway_connect_timeout_in_seconds: float = Field(default=3.0, gt=0)
    payment_gateway_read_timeout_in_seconds: float = Field(default=10.0, gt=0)
    # Idempotent gateway reads only; create-link calls are never retried (ADR 0005).
    payment_gateway_retry_max_attempts: int = Field(default=3, ge=1, le=10)
    payment_gateway_retry_base_delay_in_seconds: float = Field(default=0.2, gt=0)
    payment_gateway_retry_max_delay_in_seconds: float = Field(default=2.0, gt=0)
    payment_gateway_circuit_breaker_failure_threshold: int = Field(default=5, ge=1)
    payment_gateway_circuit_breaker_open_duration_in_seconds: float = Field(default=30.0, gt=0)
    # Paytm adapter (PAYMENT_GATEWAY_MODE=paytm). No credentials exist yet (CLAUDE.md D2); the
    # factory refuses to start without them (ADR 0004). Base URLs default to the staging hosts;
    # production hosts are not documented, so they must be set explicitly (ADR 0002).
    paytm_merchant_id: SecretStr | None = None
    paytm_merchant_key: SecretStr | None = None
    paytm_emi_subvention_base_url: str = STAGING_EMI_SUBVENTION_BASE_URL
    paytm_payment_link_base_url: str = STAGING_PAYMENT_LINK_BASE_URL
    paytm_transaction_status_base_url: str = STAGING_TRANSACTION_STATUS_BASE_URL
    paytm_webhook_callback_url: str | None = None
    log_level: LogLevel = "INFO"

    @field_validator(
        "paytm_merchant_id", "paytm_merchant_key", "paytm_webhook_callback_url", mode="before"
    )
    @classmethod
    def treat_blank_value_as_unset(cls, value: object) -> object:
        """Reads an empty or blank variable, as copied from .env.example, as not set at all."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def check_retry_delays_are_ordered(self) -> Self:
        """Rejects a base retry delay above the maximum, which would make the backoff pointless."""
        if (
            self.payment_gateway_retry_base_delay_in_seconds
            > self.payment_gateway_retry_max_delay_in_seconds
        ):
            raise ValueError(
                "PAYMENT_GATEWAY_RETRY_BASE_DELAY_IN_SECONDS must not exceed "
                "PAYMENT_GATEWAY_RETRY_MAX_DELAY_IN_SECONDS"
            )
        return self
