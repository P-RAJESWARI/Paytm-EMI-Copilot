"""GET /api/v1/payments/{orderId}/status: the shop's own sale payments only, checked server-side.

Since plan Q16 a payment made for no sale (a bare Layer 1 hand-off) is never answered here.
"""

from datetime import timedelta

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import (
    DEFAULT_PAYMENT_COMPLETION_DELAY,
    MockPaymentGatewayAdapter,
)
from emi_copilot.domain.payments import PaymentAttemptStatus
from tests.integration.api.api_harness import SAMPLE_ITEM_QUERY, ApiHarness
from tests.integration.api.sale_api_helpers import (
    COUNTER_PATH,
    SALES_PATH,
    TwoShops,
    agree_to_offer_in_the_service,
    start_sale,
)

pytestmark = pytest.mark.integration


def _create_sale_payment_link(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, headers: dict[str, str]
) -> str:
    """Agrees plan A on a new sale, creates its link and returns the status URL from Location."""
    sale_id = start_sale(mock_api, headers)["saleId"]
    agree_to_offer_in_the_service(mock_api, mock_gateway, sale_id)
    response = mock_api.client.post(
        f"{SALES_PATH}/{sale_id}/payment-links",
        headers={**headers, "Idempotency-Key": "idempotency-key-status-0001"},
    )
    assert response.status_code == 201, response.text
    return f"/api/v1/payments/{response.json()['orderId']}/status"


def test_get_payment_status_before_the_mock_delay_returns_payment_pending(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """Right after the link is made the Mock reports a pending payment and nothing paid."""
    status_url = _create_sale_payment_link(mock_api, mock_gateway, shops.first_shop_headers)
    response = mock_api.client.get(status_url, headers=shops.first_shop_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PAYMENT_PENDING"
    assert body["amountPaidInPaise"] is None


def test_get_payment_status_after_the_mock_delay_returns_paid_and_the_sale_is_paid(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """Once the Mock's delay has passed the payment is PAID, and so is the shop's sale."""
    status_url = _create_sale_payment_link(mock_api, mock_gateway, shops.first_shop_headers)
    mock_api.clock.advance(DEFAULT_PAYMENT_COMPLETION_DELAY + timedelta(seconds=1))
    response = mock_api.client.get(status_url, headers=shops.first_shop_headers)
    counter = mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers).json()
    assert response.status_code == 200
    assert response.json() == {
        "orderId": status_url.split("/")[-2],
        "status": "PAID",
        "amountPaidInPaise": 2_200_000,
    }
    assert [sale["status"] for sale in counter["sales"]] == ["PAID"]


def test_get_payment_status_of_another_shops_payment_returns_404(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """Another shop's order id looks exactly like an unknown one."""
    status_url = _create_sale_payment_link(mock_api, mock_gateway, shops.first_shop_headers)
    response = mock_api.client.get(status_url, headers=shops.second_shop_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "PAYMENT_ATTEMPT_NOT_FOUND"


def test_get_payment_status_of_a_payment_made_for_no_sale_returns_404_without_a_check(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """A Layer 1 hand-off of a bare item belongs to no shop's sale, so it is never answered."""
    link_response = mock_api.client.post(
        "/api/v1/payment-links",
        json={**SAMPLE_ITEM_QUERY, "offerId": "mock-offer-card-6m"},
        headers={**shops.first_shop_headers, "Idempotency-Key": "idempotency-key-bare-0001"},
    )
    order_id = link_response.json()["orderId"]
    mock_api.clock.advance(DEFAULT_PAYMENT_COMPLETION_DELAY)
    response = mock_api.client.get(
        f"/api/v1/payments/{order_id}/status", headers=shops.first_shop_headers
    )
    stored_attempt = mock_api.read_attempt(order_id)
    assert response.status_code == 404
    assert stored_attempt is not None
    assert stored_attempt.status is PaymentAttemptStatus.LINK_CREATED


def test_get_payment_status_for_unknown_order_returns_404_problem(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """An order id that is not ours is not found."""
    response = mock_api.client.get(
        "/api/v1/payments/01JD0000000000000000UNKNWN/status", headers=shops.first_shop_headers
    )
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "PAYMENT_ATTEMPT_NOT_FOUND"


def test_get_payment_status_without_a_merchant_token_returns_401(mock_api: ApiHarness) -> None:
    """Since Layer 2 the status of a payment is the signed-in shop's business only (plan Q16)."""
    response = mock_api.client.get("/api/v1/payments/01JD0000000000000000UNKNWN/status")
    assert response.status_code == 401
    assert response.json()["code"] == "MERCHANT_AUTHENTICATION_REQUIRED"
