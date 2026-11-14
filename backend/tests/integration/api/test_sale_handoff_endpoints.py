"""M4 hand-off endpoints on PostgreSQL with the Mock gateway: links, status and merchant scope."""

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import (
    DEFAULT_PAYMENT_COMPLETION_DELAY,
    MockPaymentGatewayAdapter,
)
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import GatewayPaymentStatus
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import ApiHarness, open_api_harness
from tests.integration.api.sale_api_helpers import (
    COUNTER_PATH,
    SALES_PATH,
    TwoShops,
    agree_to_offer_in_the_service,
    start_sale,
    store_and_pair_two_shops,
)

pytestmark = pytest.mark.integration

WEBHOOK_PATH = "/api/v1/webhooks/paytm"
HANDOFF_KEYS = {
    "sale",
    "edcInstructions",
    "latestPaymentLink",
    "paymentStatus",
    "paymentConfirmedAt",
}


def _start_agreed_sale(
    harness: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, headers: dict[str, str]
) -> str:
    """Starts a sale of the 128 GB phone and agrees design plan A on it; gives its id."""
    sale_id: str = start_sale(harness, headers)["saleId"]
    agree_to_offer_in_the_service(harness, mock_gateway, sale_id)
    return sale_id


def _create_link(
    harness: ApiHarness, headers: dict[str, str], sale_id: str, key: str = "sale-link-key-0001"
) -> dict[str, Any]:
    """Creates the sale's payment link and gives the 201 body."""
    response = harness.client.post(
        f"{SALES_PATH}/{sale_id}/payment-links", headers={**headers, "Idempotency-Key": key}
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _read_handoff(harness: ApiHarness, headers: dict[str, str], sale_id: str) -> dict[str, Any]:
    """Reads the sale's hand-off and gives the 200 body."""
    response = harness.client.get(f"{SALES_PATH}/{sale_id}/handoff", headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_get_handoff_of_an_agreed_sale_shows_plan_totals_edc_steps_and_waiting(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """M4 before a link: Brand EMI on the ₹22,000 price, plan A with its extra and total."""
    sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    response = mock_api.client.get(
        f"{SALES_PATH}/{sale_id}/handoff", headers=shops.first_shop_headers
    )
    body = response.json()
    assert response.headers["Cache-Control"] == "no-store"
    assert set(body) == HANDOFF_KEYS
    assert body["sale"]["status"] == "READY_TO_PAY"
    assert body["sale"]["chosenPlan"]["extraInTotalInPaise"] == 0
    assert body["sale"]["chosenPlan"]["totalPayableInPaise"] == 2_200_000
    assert body["edcInstructions"] == {
        "emiProgramme": "BRAND_EMI",
        "productName": "Example phone, 128 GB",
        "tenureInMonths": 6,
        "isNoExtraCost": True,
        "amountInPaise": 2_200_000,
    }
    assert body["latestPaymentLink"] is None
    assert (body["paymentStatus"], body["paymentConfirmedAt"]) == ("WAITING", None)


def test_create_sale_payment_link_returns_201_and_replays_the_same_body(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """One link per key: the replay is identical, and the hand-off now shows the link."""
    sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    path = f"{SALES_PATH}/{sale_id}/payment-links"
    headers = {**shops.first_shop_headers, "Idempotency-Key": "sale-link-key-0001"}
    first_response = mock_api.client.post(path, headers=headers)
    replay_response = mock_api.client.post(path, headers=headers)
    body = first_response.json()
    assert first_response.status_code == 201
    assert first_response.headers["Location"] == f"{SALES_PATH}/{sale_id}/handoff"
    assert set(body) == {"orderId", "paymentUrl", "amountInPaise", "status"}
    assert (body["amountInPaise"], body["status"]) == (2_200_000, "AWAITING_PAYMENT")
    assert replay_response.json() == body
    assert _read_handoff(mock_api, shops.first_shop_headers, sale_id)["latestPaymentLink"] == {
        "orderId": body["orderId"],
        "paymentUrl": body["paymentUrl"],
        "status": "AWAITING_PAYMENT",
    }


def test_create_sale_payment_link_without_idempotency_key_is_refused_as_layer_1_does(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """The key is required; its absence is the same 422 field error as on Layer 1."""
    sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    response = mock_api.client.post(
        f"{SALES_PATH}/{sale_id}/payment-links", headers=shops.first_shop_headers
    )
    assert response.status_code == 422
    assert response.json()["fieldErrors"] == [
        {"field": "Idempotency-Key", "message": "Field required"}
    ]


def test_create_sale_payment_link_with_a_key_used_on_another_sale_is_422_key_reused(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """The sale id is part of the body, so a key cannot jump to another sale."""
    first_sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    second_sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    _create_link(mock_api, shops.first_shop_headers, first_sale_id)
    response = mock_api.client.post(
        f"{SALES_PATH}/{second_sale_id}/payment-links",
        headers={**shops.first_shop_headers, "Idempotency-Key": "sale-link-key-0001"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_hand_off_endpoints_on_a_choosing_sale_answer_409_sale_state_conflict(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """No agreed plan yet: nothing to show, link or check."""
    sale_id = start_sale(mock_api, shops.first_shop_headers)["saleId"]
    headers = {**shops.first_shop_headers, "Idempotency-Key": "sale-link-key-0001"}
    responses = [
        mock_api.client.get(f"{SALES_PATH}/{sale_id}/handoff", headers=headers),
        mock_api.client.post(f"{SALES_PATH}/{sale_id}/payment-links", headers=headers),
        mock_api.client.get(f"{SALES_PATH}/{sale_id}/payment-status", headers=headers),
    ]
    assert [response.status_code for response in responses] == [409, 409, 409]
    assert {response.json()["code"] for response in responses} == {"SALE_STATE_CONFLICT"}


def test_hand_off_endpoints_on_another_shops_sale_answer_404(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """Another shop's sale looks exactly like a sale that does not exist."""
    sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    headers = {**shops.second_shop_headers, "Idempotency-Key": "sale-link-key-0001"}
    responses = [
        mock_api.client.get(f"{SALES_PATH}/{sale_id}/handoff", headers=headers),
        mock_api.client.post(f"{SALES_PATH}/{sale_id}/payment-links", headers=headers),
        mock_api.client.get(f"{SALES_PATH}/{sale_id}/payment-status", headers=headers),
    ]
    assert [response.status_code for response in responses] == [404, 404, 404]
    assert {response.json()["code"] for response in responses} == {"SALE_NOT_FOUND"}


def test_hand_off_endpoints_without_a_token_answer_401(mock_api: ApiHarness) -> None:
    """Every hand-off endpoint is a merchant endpoint."""
    sale_path = f"{SALES_PATH}/01JD5Z0Q8M6X3V2N7B4C9K1T0F"
    responses = [
        mock_api.client.get(f"{sale_path}/handoff"),
        mock_api.client.post(f"{sale_path}/payment-links", headers={"Idempotency-Key": "k" * 8}),
        mock_api.client.get(f"{sale_path}/payment-status"),
    ]
    assert [response.status_code for response in responses] == [401, 401, 401]


def test_verified_paid_webhook_moves_the_sale_to_paid_on_the_counter_and_hand_off(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """The gateway's signed PAID report is the only way a sale becomes PAID."""
    sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    order_id = _create_link(mock_api, shops.first_shop_headers, sale_id)["orderId"]
    mock_api.clock.advance(timedelta(minutes=3))
    notification = mock_gateway.build_signed_notification(
        order_id, GatewayPaymentStatus.PAID, "mock-transaction-0001", Money.from_paise(2_200_000)
    )
    webhook_response = mock_api.client.post(WEBHOOK_PATH, data=dict(notification.received_fields))
    handoff = _read_handoff(mock_api, shops.first_shop_headers, sale_id)
    counter = mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers).json()
    assert webhook_response.status_code == 202
    assert handoff["paymentStatus"] == "PAID"
    assert handoff["paymentConfirmedAt"] is not None
    assert handoff["latestPaymentLink"]["status"] == "PAID"
    assert [sale["status"] for sale in counter["sales"]] == ["PAID"]


def test_check_sale_payment_status_asks_the_gateway_and_applies_its_answer(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """Before the Mock's delay the payment is waiting; after it, the check confirms PAID."""
    sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    _create_link(mock_api, shops.first_shop_headers, sale_id)
    status_path = f"{SALES_PATH}/{sale_id}/payment-status"
    waiting = mock_api.client.get(status_path, headers=shops.first_shop_headers).json()
    mock_api.clock.advance(DEFAULT_PAYMENT_COMPLETION_DELAY)
    paid = mock_api.client.get(status_path, headers=shops.first_shop_headers).json()
    assert waiting == {"paymentStatus": "WAITING", "paymentConfirmedAt": None}
    assert paid["paymentStatus"] == "PAID"
    assert paid["paymentConfirmedAt"] is not None


def test_payment_not_completed_then_a_new_link_retries_the_sale(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """A failed payment shows NOT_COMPLETED; a new key makes a new link and READY_TO_PAY again."""
    sale_id = _start_agreed_sale(mock_api, mock_gateway, shops.first_shop_headers)
    first_order_id = _create_link(mock_api, shops.first_shop_headers, sale_id)["orderId"]
    mock_gateway.simulate_payment_outcome(first_order_id, GatewayPaymentStatus.FAILED)
    status_path = f"{SALES_PATH}/{sale_id}/payment-status"
    failed = mock_api.client.get(status_path, headers=shops.first_shop_headers).json()
    second_link = _create_link(mock_api, shops.first_shop_headers, sale_id, "sale-link-key-0002")
    handoff = _read_handoff(mock_api, shops.first_shop_headers, sale_id)
    assert failed["paymentStatus"] == "NOT_COMPLETED"
    assert second_link["orderId"] != first_order_id
    assert handoff["sale"]["status"] == "READY_TO_PAY"
    assert handoff["latestPaymentLink"]["orderId"] == second_link["orderId"]


@pytest.fixture
def tightly_limited_api(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
) -> Iterator[ApiHarness]:
    """Runs the application with two gateway-backed merchant calls a minute per shop."""
    settings = ApplicationSettings(merchant_payment_rate_limit_max_requests=2)
    with open_api_harness(session_factory, fixed_clock, mock_gateway, settings) as harness:
        yield harness


def test_payment_calls_over_the_shops_limit_answer_429_with_retry_after(
    tightly_limited_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter
) -> None:
    """Links and status checks share the shop's limit; another shop is not affected."""
    shops = store_and_pair_two_shops(tightly_limited_api)
    sale_id = _start_agreed_sale(tightly_limited_api, mock_gateway, shops.first_shop_headers)
    status_path = f"{SALES_PATH}/{sale_id}/payment-status"
    _create_link(tightly_limited_api, shops.first_shop_headers, sale_id)
    allowed = tightly_limited_api.client.get(status_path, headers=shops.first_shop_headers)
    refused = tightly_limited_api.client.get(status_path, headers=shops.first_shop_headers)
    other_shop = tightly_limited_api.client.get(status_path, headers=shops.second_shop_headers)
    assert allowed.status_code == 200
    assert refused.status_code == 429
    assert refused.json()["code"] == "RATE_LIMITED"
    assert int(refused.headers["Retry-After"]) >= 1
    assert other_shop.status_code == 404
