"""Typed configuration of the Paytm adapter: merchant credentials, base URLs and HTTP clients.

The merchant id and key are SecretStr, so neither prints in a repr or a log line. Every URL must
be absolute https; the base URLs default to Paytm's staging hosts in settings (ADR 0002).
"""

from dataclasses import dataclass
from urllib.parse import urlsplit

from pydantic import SecretStr

from emi_copilot.core.resilient_http_client import ResilientHttpClient


def _require_https_url(url: str, description: str) -> None:
    """Raises unless the URL is absolute https with a host; plain http is never configured."""
    split_url = urlsplit(url)
    if split_url.scheme != "https" or not split_url.hostname:
        raise ValueError(f"The {description} must be an absolute https URL.")


@dataclass(frozen=True, slots=True)
class PaytmGatewayConfiguration:
    """What the adapter needs from configuration; the merchant id and key never print."""

    merchant_id: SecretStr
    merchant_key: SecretStr
    emi_subvention_base_url: str
    payment_link_base_url: str
    transaction_status_base_url: str
    webhook_callback_url: str | None

    def __post_init__(self) -> None:
        """Rejects a blank merchant id and any URL that is not absolute https."""
        if not self.merchant_id.get_secret_value().strip():
            raise ValueError("The merchant id must be non-empty.")
        _require_https_url(self.emi_subvention_base_url, "EMI subvention base URL")
        _require_https_url(self.payment_link_base_url, "payment link base URL")
        _require_https_url(self.transaction_status_base_url, "transaction status base URL")
        if self.webhook_callback_url is not None:
            _require_https_url(self.webhook_callback_url, "webhook callback URL")


@dataclass(frozen=True, slots=True)
class PaytmHttpClients:
    """One resilient client per Paytm API family; the factory may pass one client for all three."""

    emi_subvention: ResilientHttpClient
    payment_link: ResilientHttpClient
    transaction_status: ResilientHttpClient
