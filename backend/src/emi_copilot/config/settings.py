"""Typed application settings read from environment variables."""

import re
from datetime import timedelta
from enum import StrEnum
from typing import Literal, Self
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# The fixed one-time code the Mock OTP sender's customers type (ADR 0022); never a real code.
DEFAULT_MOCK_CONSENT_OTP_CODE = "123456"  # pragma: allowlist secret
_SIX_DIGITS_PATTERN = re.compile(r"[0-9]{6}")

# The Vite dev server of customer-web (frontend/apps/customer-web); the QR code opens it.
LOCAL_CUSTOMER_WEB_BASE_URL = "http://localhost:5174"
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
    # Mock adapter (the default). Signs and verifies simulated webhooks; at least 32 bytes. When
    # unset, the gateway factory draws a random secret once per process.
    mock_gateway_webhook_signing_secret: SecretStr | None = None
    # Paytm adapter (PAYMENT_GATEWAY_MODE=paytm). No credentials exist yet (CLAUDE.md D2); the
    # factory refuses to start without them (ADR 0004). An unset base URL gets the staging host
    # from the gateway factory, which owns every Paytm detail (ADR 0011); production hosts are
    # not documented, so they must be set explicitly (ADR 0002).
    paytm_merchant_id: SecretStr | None = None
    paytm_merchant_key: SecretStr | None = None
    paytm_emi_subvention_base_url: str | None = None
    paytm_payment_link_base_url: str | None = None
    paytm_transaction_status_base_url: str | None = None
    paytm_webhook_callback_url: str | None = None
    # Merchant device pairing (plan Q18): a paired device's bearer token lasts 12 hours, and each
    # client address may try pairing this many times per window (in-memory, per process).
    merchant_access_token_lifetime_in_seconds: int = Field(default=43_200, ge=60, le=604_800)
    merchant_pairing_rate_limit_max_requests: int = Field(default=10, ge=1)
    merchant_pairing_rate_limit_window_in_seconds: int = Field(default=60, ge=1)
    # Gateway-backed merchant calls (payment links and status checks, plan Q16): each shop may
    # make this many per window (in-memory, per process).
    merchant_payment_rate_limit_max_requests: int = Field(default=60, ge=1)
    merchant_payment_rate_limit_window_in_seconds: int = Field(default=60, ge=1)
    # Gateway webhooks: a generous per-client-address limit, so a flood cannot exhaust the
    # signature checks while the gateway's real retries always get through.
    payment_webhook_rate_limit_max_requests: int = Field(default=600, ge=1)
    payment_webhook_rate_limit_window_in_seconds: int = Field(default=60, ge=1)
    # Customer QR codes (plan Q18). HMAC-SHA256 key, at least 32 bytes; when unset in Mock gateway
    # mode a random per-process key is drawn (QR codes then stop working after a restart), and
    # Paytm mode refuses to start without it. A QR token lasts 15 minutes and can be re-issued.
    customer_qr_signing_secret: SecretStr | None = None
    customer_qr_token_lifetime_in_seconds: int = Field(default=900, ge=60, le=86_400)
    customer_web_base_url: str = LOCAL_CUSTOMER_WEB_BASE_URL
    # A sale still CHOOSING this long after it started expires (plan Q18).
    sale_choosing_expiry_in_seconds: int = Field(default=3_600, ge=60, le=86_400)
    # Live sale status streams: how many unread messages one stream may hold before its backlog
    # is replaced by a single resync message, and how often a quiet stream sends a heartbeat.
    sale_event_stream_maximum_queued_messages: int = Field(default=100, ge=1, le=10_000)
    sale_event_stream_heartbeat_interval_in_seconds: float = Field(default=15.0, gt=0, le=300)
    # MockCustomerSimulator (plan step 2.3, rules 9 and 10): demo-only endpoints that play the
    # customer agreeing to a plan and paying a Mock link. Off by default; refused in paytm mode.
    mock_customer_simulator_enabled: bool = False
    # Customer sessions and consent one-time codes (ADR 0022 decision 3, demo values). A session
    # lasts 30 minutes; a code allows 3 attempts, lasts 5 minutes and can be resent after 30 s.
    customer_session_lifetime_in_seconds: int = Field(default=1_800, ge=60, le=86_400)
    consent_otp_lifetime_in_seconds: int = Field(default=300, ge=30, le=3_600)
    consent_otp_maximum_attempts: int = Field(default=3, ge=1, le=10)
    consent_otp_resend_wait_in_seconds: int = Field(default=30, ge=1, le=600)
    # The Mock OTP sender sends nothing, so its customers type this fixed six-digit code. It is
    # never logged; a real sender would use random codes instead.
    mock_consent_otp_code: SecretStr = SecretStr(DEFAULT_MOCK_CONSENT_OTP_CODE)
    # HMAC-SHA256 key for the customer's phone hash and consent code hashes, at least 32 bytes.
    # When unset in Mock gateway mode a random per-process key is drawn (stored phone hashes
    # then differ after a restart); Paytm mode refuses to start without it.
    customer_phone_hash_secret: SecretStr | None = None
    # The shop's calendar: "today" on the counter list and the report periods (plan Q21).
    reporting_time_zone: str = "Asia/Kolkata"
    log_level: LogLevel = "INFO"

    @property
    def payment_link_creation_stale_after(self) -> timedelta:
        """Gives twice the longest one create-link call can wait: connect plus read timeout.

        A replay finding an attempt in progress for longer stores it as OUTCOME_UNKNOWN (Layer 1
        handoff question 2): by then that call has surely ended, so its process must have died.
        """
        longest_call_in_seconds = (
            self.payment_gateway_connect_timeout_in_seconds
            + self.payment_gateway_read_timeout_in_seconds
        )
        return 2 * timedelta(seconds=longest_call_in_seconds)

    @field_validator(
        "mock_gateway_webhook_signing_secret",
        "paytm_merchant_id",
        "paytm_merchant_key",
        "paytm_emi_subvention_base_url",
        "paytm_payment_link_base_url",
        "paytm_transaction_status_base_url",
        "paytm_webhook_callback_url",
        "customer_qr_signing_secret",
        "customer_phone_hash_secret",
        mode="before",
    )
    @classmethod
    def treat_blank_value_as_unset(cls, value: object) -> object:
        """Reads an empty or blank variable, as copied from .env.example, as not set at all."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("customer_web_base_url")
    @classmethod
    def check_customer_web_base_url(cls, value: str) -> str:
        """Accepts an http(s) origin and path only, without query or fragment; drops a final /.

        The QR token is appended as the fragment, so the base must not carry one itself.
        """
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("CUSTOMER_WEB_BASE_URL must be an http or https URL with a host")
        if parts.query or parts.fragment:
            raise ValueError("CUSTOMER_WEB_BASE_URL must not have a query or a fragment")
        return value.rstrip("/")

    @field_validator("mock_consent_otp_code")
    @classmethod
    def check_mock_consent_otp_code(cls, value: SecretStr) -> SecretStr:
        """Accepts exactly six digits, the code length the consent screen asks for."""
        if _SIX_DIGITS_PATTERN.fullmatch(value.get_secret_value()) is None:
            raise ValueError("MOCK_CONSENT_OTP_CODE must be exactly six digits")
        return value

    @field_validator("reporting_time_zone")
    @classmethod
    def check_reporting_time_zone(cls, value: str) -> str:
        """Accepts an IANA time zone name such as Asia/Kolkata, so day boundaries are exact."""
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as unknown_zone_error:
            raise ValueError("REPORTING_TIME_ZONE must be an IANA time zone name") from (
                unknown_zone_error
            )
        return value

    @model_validator(mode="after")
    def refuse_mock_customer_simulator_with_the_real_gateway(self) -> Self:
        """Refuses to start with the simulator on in paytm mode: it can only pay Mock links."""
        if (
            self.mock_customer_simulator_enabled
            and self.payment_gateway_mode is PaymentGatewayMode.PAYTM
        ):
            raise ValueError(
                "MOCK_CUSTOMER_SIMULATOR_ENABLED=true is refused with PAYMENT_GATEWAY_MODE=paytm"
            )
        return self

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

    @model_validator(mode="after")
    def check_consent_otp_resend_wait_is_within_its_lifetime(self) -> Self:
        """Rejects a resend wait as long as the code's lifetime, which would block every resend."""
        if self.consent_otp_resend_wait_in_seconds >= self.consent_otp_lifetime_in_seconds:
            raise ValueError(
                "CONSENT_OTP_RESEND_WAIT_IN_SECONDS must be below CONSENT_OTP_LIFETIME_IN_SECONDS"
            )
        return self
