"""No log record of pairing and signed-in requests holds the PIN, the token or the header."""

import logging
from datetime import timedelta

import pytest

from emi_copilot.core.logging import extract_extra_fields
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.merchant_api_helpers import (
    PAIRING_PATH,
    WRONG_PIN,
    store_demo_catalogue,
    store_shop,
)

pytestmark = pytest.mark.integration

MERCHANT_ID = "01JCMERCHANTLOGGING0000001"
SYNTHETIC_UNKNOWN_BEARER_VALUE = "synthetic-unknown-bearer-value-for-logging"


def render_log_records(records: list[logging.LogRecord]) -> str:
    """Joins each record's message and caller extras, leaving out timestamps and thread ids."""
    return "\n".join(
        f"{record.getMessage()} {extract_extra_fields(record)} {record.exc_text or ''}"
        for record in records
    )


def test_pairing_and_merchant_requests_never_log_pin_token_or_authorization(
    mock_api: ApiHarness, caplog: pytest.LogCaptureFixture
) -> None:
    """Wrong PINs, the lock, a pairing, the profile, the catalogue and a bad token: no secret.

    The records are read before any redaction filter runs, so nothing was logged to redact.
    """
    shop = store_shop(mock_api, MERCHANT_ID, "SHOP-LOGS")
    store_demo_catalogue(mock_api, MERCHANT_ID, "01JCPRODUCTLOGGING000000")
    with caplog.at_level(logging.DEBUG):
        for _ in range(5):
            mock_api.client.post(PAIRING_PATH, json={"shopId": shop.shop_code, "pin": WRONG_PIN})
        mock_api.clock.advance(timedelta(minutes=15))
        pairing_response = mock_api.client.post(
            PAIRING_PATH, json={"shopId": shop.shop_code, "pin": shop.pin}
        )
        access_token = pairing_response.json()["accessToken"]
        bearer_headers = {"Authorization": f"Bearer {access_token}"}
        mock_api.client.get("/api/v1/merchants/me", headers=bearer_headers)
        mock_api.client.get("/api/v1/products", headers=bearer_headers)
        mock_api.client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": f"Bearer {SYNTHETIC_UNKNOWN_BEARER_VALUE}"},
        )
    logged_text = render_log_records(caplog.records)
    assert "merchant device paired" in logged_text
    assert "pairing locked after repeated wrong PINs" in logged_text
    for secret_text in (
        access_token,
        SYNTHETIC_UNKNOWN_BEARER_VALUE,
        shop.pin,
        WRONG_PIN,
        "Bearer",
    ):
        assert secret_text not in logged_text


def test_sale_requests_never_log_the_qr_token_or_its_url(
    mock_api: ApiHarness, caplog: pytest.LogCaptureFixture
) -> None:
    """Starting a sale and re-issuing its QR code log neither the token nor the customer URL."""
    shop = store_shop(mock_api, "01JCMERCHANTLOGGING0000002", "SHOP-LOGS-QR")
    store_demo_catalogue(mock_api, shop.merchant_id, "01JCPRODUCTLOGGINGQR0000")
    pairing_response = mock_api.client.post(
        PAIRING_PATH, json={"shopId": shop.shop_code, "pin": shop.pin}
    )
    bearer_headers = {"Authorization": f"Bearer {pairing_response.json()['accessToken']}"}
    with caplog.at_level(logging.DEBUG):
        sale = mock_api.client.post(
            "/api/v1/sales",
            json={"productId": "01JCPRODUCTLOGGINGQR000000"},
            headers=bearer_headers,
        ).json()
        reissued_qr = mock_api.client.post(
            f"/api/v1/sales/{sale['saleId']}/qr-tokens", headers=bearer_headers
        ).json()
        mock_api.client.get("/api/v1/sales?view=counter", headers=bearer_headers)
    logged_text = render_log_records(caplog.records)
    for customer_url in (sale["qr"]["customerUrl"], reissued_qr["customerUrl"]):
        assert customer_url.split("#t=")[1] not in logged_text
    assert "#t=" not in logged_text
