"""GET /api/v1/payments/{orderId}/status, confirmed with the Mock gateway server-side."""

from datetime import timedelta

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import DEFAULT_PAYMENT_COMPLETION_DELAY
from tests.integration.api.api_harness import SAMPLE_ITEM_QUERY, ApiHarness

pytestmark = pytest.mark.integration


def _create_payment_link(mock_api: ApiHarness) -> str:
    """Creates a link for design plan B and returns the status URL from Location."""
    response = mock_api.client.post(
        "/api/v1/payment-links",
        json={**SAMPLE_ITEM_QUERY, "offerId": "mock-offer-card-6m"},
        headers={"Idempotency-Key": "idempotency-key-status-0001"},
    )
    assert response.status_code == 201
    status_url: str = response.headers["Location"]
    return status_url


def test_get_payment_status_before_the_mock_delay_returns_payment_pending(
    mock_api: ApiHarness,
) -> None:
    """Right after the link is made the Mock reports a pending payment and nothing paid."""
    status_url = _create_payment_link(mock_api)
    response = mock_api.client.get(status_url)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PAYMENT_PENDING"
    assert body["amountPaidInPaise"] is None


def test_get_payment_status_after_the_mock_delay_returns_paid_with_amount(
    mock_api: ApiHarness,
) -> None:
    """Once the Mock's completion delay has passed the payment is PAID with the full amount."""
    status_url = _create_payment_link(mock_api)
    mock_api.clock.advance(DEFAULT_PAYMENT_COMPLETION_DELAY + timedelta(seconds=1))
    response = mock_api.client.get(status_url)
    assert response.status_code == 200
    order_id = status_url.split("/")[-2]
    assert response.json() == {
        "orderId": order_id,
        "status": "PAID",
        "amountPaidInPaise": 2_200_000,
    }


def test_get_payment_status_for_unknown_order_returns_404_problem(mock_api: ApiHarness) -> None:
    """An order id that is not ours is not found."""
    response = mock_api.client.get("/api/v1/payments/01JD0000000000000000UNKNWN/status")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "PAYMENT_ATTEMPT_NOT_FOUND"
