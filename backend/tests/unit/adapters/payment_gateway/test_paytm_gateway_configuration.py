"""PaytmGatewayConfiguration: https-only URLs, a merchant id, and credentials that never print."""

import dataclasses

import pytest
from pydantic import SecretStr

from tests.contract.payment_gateway.paytm_adapter_builder import build_synthetic_configuration
from tests.contract.payment_gateway.paytm_fake_server import (
    SYNTHETIC_MERCHANT_ID,
    SYNTHETIC_MERCHANT_KEY,
)


def test_paytm_gateway_configuration_repr_hides_merchant_id_and_key() -> None:
    """Printing or logging the configuration reveals neither credential."""
    configuration_text = repr(build_synthetic_configuration())
    assert SYNTHETIC_MERCHANT_ID not in configuration_text
    assert SYNTHETIC_MERCHANT_KEY not in configuration_text


@pytest.mark.parametrize(
    "unusable_field",
    [
        {"emi_subvention_base_url": "http://securestage.example.test"},
        {"payment_link_base_url": "securestage.example.test"},
        {"transaction_status_base_url": "https://"},
        {"webhook_callback_url": "http://emi-copilot.example.test/webhooks"},
        {"merchant_id": SecretStr("  ")},
    ],
    ids=["http-base", "no-scheme", "no-host", "http-callback", "blank-merchant-id"],
)
def test_paytm_gateway_configuration_refuses_non_https_urls_and_blank_merchant_id(
    unusable_field: dict[str, object],
) -> None:
    """Every URL must be absolute https, so TLS is always used; the merchant id is required."""
    with pytest.raises(ValueError, match="must be"):
        dataclasses.replace(build_synthetic_configuration(), **unusable_field)  # type: ignore[arg-type]


def test_paytm_gateway_configuration_allows_no_webhook_callback_url() -> None:
    """Without a callback URL the configuration is still valid; links just carry none."""
    assert build_synthetic_configuration(webhook_callback_url=None).webhook_callback_url is None
