"""Typed application settings read from environment variables."""

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    log_level: LogLevel = "INFO"

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
