"""MockCustomerSimulator on PostgreSQL: gated, hidden from the schema, and the demo path to PAID.

The full path here is the one the Playwright run takes: pair, start a sale, agree as the
customer, create the link, pay as the customer, and see PAID on the hand-off and live stream.
"""

import asyncio
import json
import logging
from collections.abc import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
from emi_copilot.main import MOCK_CUSTOMER_SIMULATOR_ACTIVE_WARNING, create_application
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import ApiHarness, open_api_harness
from tests.integration.api.asgi_event_stream import AsgiEventStream
from tests.integration.api.merchant_api_helpers import (
    PAIRING_PATH,
    store_demo_catalogue,
    store_shop,
)
from tests.integration.api.sale_api_helpers import (
    NO_COST_OFFER_ID,
    SALES_PATH,
    TwoShops,
    start_sale,
    store_and_pair_two_shops,
)
from tests.integration.api.test_merchant_logging import render_log_records

pytestmark = pytest.mark.integration

SIMULATOR_PATH = "/api/v1/mock-customer-simulator"
SIMULATOR_SETTINGS = ApplicationSettings(
    mock_customer_simulator_enabled=True, sale_event_stream_heartbeat_interval_in_seconds=0.05
)


@pytest.fixture
def simulator_api(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
) -> Iterator[ApiHarness]:
    """Runs the application on the Mock gateway with the simulator switched on."""
    with open_api_harness(
        session_factory, fixed_clock, mock_gateway, SIMULATOR_SETTINGS
    ) as harness:
        yield harness


@pytest.fixture
def simulator_shops(simulator_api: ApiHarness) -> TwoShops:
    """Two paired shops with the M2 catalogue on the simulator application."""
    return store_and_pair_two_shops(simulator_api)


def _agree(harness: ApiHarness, headers: dict[str, str], sale_id: str) -> dict[str, object]:
    """Agrees design plan A on the sale as the simulated customer; gives the 200 body."""
    response = harness.client.post(
        f"{SIMULATOR_PATH}/sales/{sale_id}/agreed-plan",
        json={"offerId": NO_COST_OFFER_ID},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def test_simulator_agree_moves_the_sale_to_ready_to_pay_and_streams_it_live(
    simulator_api: ApiHarness, simulator_shops: TwoShops
) -> None:
    """The agreement is announced on the shop's open stream as READY_TO_PAY."""
    headers = simulator_shops.first_shop_headers
    sale_id = start_sale(simulator_api, headers)["saleId"]

    async def scenario() -> tuple[dict[str, object], dict[str, object]]:
        """Opens the stream, agrees through the simulator endpoint and reads the next event."""
        stream = AsgiEventStream(simulator_api.client.app, f"{SALES_PATH}/events", headers)
        await stream.open()
        summary = await asyncio.to_thread(_agree, simulator_api, headers, sale_id)
        frame = await stream.read_frame_other_than_heartbeat()
        await stream.close()
        assert frame is not None
        return summary, json.loads(frame.split("\n")[1].removeprefix("data: "))

    summary, event = asyncio.run(scenario())
    assert summary["status"] == "READY_TO_PAY"
    assert event == {
        "saleId": sale_id,
        "status": "READY_TO_PAY",
        "statusChangedAt": summary["statusChangedAt"],
    }


def test_demo_path_reaches_paid_through_the_verified_webhook_path(
    simulator_api: ApiHarness, simulator_shops: TwoShops
) -> None:
    """Agree, link, pay as the customer: the Mock's signed report makes the sale PAID."""
    headers = simulator_shops.first_shop_headers
    sale_id = start_sale(simulator_api, headers)["saleId"]
    _agree(simulator_api, headers, sale_id)
    link = simulator_api.client.post(
        f"{SALES_PATH}/{sale_id}/payment-links",
        headers={**headers, "Idempotency-Key": "demo-path-link-key-0001"},
    ).json()
    completed = simulator_api.client.post(
        f"{SIMULATOR_PATH}/payments/{link['orderId']}/completed", headers=headers
    )
    handoff = simulator_api.client.get(f"{SALES_PATH}/{sale_id}/handoff", headers=headers).json()
    status = simulator_api.client.get(
        f"/api/v1/payments/{link['orderId']}/status", headers=headers
    ).json()
    assert completed.status_code == 202
    assert completed.content == b""
    assert handoff["paymentStatus"] == "PAID"
    assert handoff["sale"]["status"] == "PAID"
    assert status["status"] == "PAID"


def test_simulator_refuses_another_shops_sale_and_payment_with_404(
    simulator_api: ApiHarness, simulator_shops: TwoShops
) -> None:
    """The simulator acts only for the signed-in shop."""
    sale_id = start_sale(simulator_api, simulator_shops.first_shop_headers)["saleId"]
    _agree(simulator_api, simulator_shops.first_shop_headers, sale_id)
    link = simulator_api.client.post(
        f"{SALES_PATH}/{sale_id}/payment-links",
        headers={**simulator_shops.first_shop_headers, "Idempotency-Key": "other-shop-key-01"},
    ).json()
    other_headers = simulator_shops.second_shop_headers
    agree_response = simulator_api.client.post(
        f"{SIMULATOR_PATH}/sales/{sale_id}/agreed-plan",
        json={"offerId": NO_COST_OFFER_ID},
        headers=other_headers,
    )
    pay_response = simulator_api.client.post(
        f"{SIMULATOR_PATH}/payments/{link['orderId']}/completed", headers=other_headers
    )
    assert (agree_response.status_code, agree_response.json()["code"]) == (404, "SALE_NOT_FOUND")
    assert (pay_response.status_code, pay_response.json()["code"]) == (
        404,
        "PAYMENT_ATTEMPT_NOT_FOUND",
    )


def test_simulator_without_a_token_answers_401(simulator_api: ApiHarness) -> None:
    """The shop's bearer token is required, as on every merchant endpoint."""
    response = simulator_api.client.post(
        f"{SIMULATOR_PATH}/sales/01JD5Z0Q8M6X3V2N7B4C9K1T0F/agreed-plan",
        json={"offerId": NO_COST_OFFER_ID},
    )
    assert response.status_code == 401


def test_simulator_is_absent_when_disabled_and_from_the_schema_when_enabled(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """Off by default (404 like any unknown route); on, it is still not in openapi.json."""
    sale_id = start_sale(mock_api, shops.first_shop_headers)["saleId"]
    response = mock_api.client.post(
        f"{SIMULATOR_PATH}/sales/{sale_id}/agreed-plan",
        json={"offerId": NO_COST_OFFER_ID},
        headers=shops.first_shop_headers,
    )
    enabled_schema = create_application(SIMULATOR_SETTINGS).openapi()
    assert (response.status_code, response.json()["code"]) == (404, "RESOURCE_NOT_FOUND")
    assert not [path for path in enabled_schema["paths"] if "simulator" in path]


def test_simulator_is_announced_in_the_startup_log_only_when_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Rule 10: anything not real says so when the server starts."""
    with caplog.at_level(logging.WARNING):
        create_application(ApplicationSettings())
        assert MOCK_CUSTOMER_SIMULATOR_ACTIVE_WARNING not in caplog.text
        create_application(SIMULATOR_SETTINGS)
    assert MOCK_CUSTOMER_SIMULATOR_ACTIVE_WARNING in caplog.text


def test_simulator_is_refused_at_startup_with_the_real_gateway() -> None:
    """It can only pay Mock links, so paytm mode with the simulator on does not start."""
    with pytest.raises(ValidationError, match="MOCK_CUSTOMER_SIMULATOR_ENABLED"):
        ApplicationSettings(
            mock_customer_simulator_enabled=True, payment_gateway_mode=PaymentGatewayMode.PAYTM
        )


def test_simulator_payment_on_a_gateway_that_is_not_the_mock_is_a_wiring_error(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """With a test double gateway the payment control does not exist: a 500, never a guess."""
    with open_api_harness(
        session_factory, fixed_clock, FakePaymentGateway(), SIMULATOR_SETTINGS
    ) as harness:
        shops = store_and_pair_two_shops(harness)
        response = harness.client.post(
            f"{SIMULATOR_PATH}/payments/ORDER-ANY-0001/completed",
            headers=shops.first_shop_headers,
        )
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"


def test_demo_path_never_logs_tokens_authorization_or_payment_urls(
    simulator_api: ApiHarness, caplog: pytest.LogCaptureFixture
) -> None:
    """Pairing, streaming, agreeing, linking, paying and checking leave no secret in the log."""
    shop = store_shop(simulator_api, "01JCMERCHANTSIMULATOR00001", "SHOP-SIMULATOR")
    store_demo_catalogue(simulator_api, shop.merchant_id, "01JCPRODUCTSIMULATOR0000")
    with caplog.at_level(logging.DEBUG):
        pairing = simulator_api.client.post(
            PAIRING_PATH, json={"shopId": shop.shop_code, "pin": shop.pin}
        ).json()
        headers = {"Authorization": f"Bearer {pairing['accessToken']}"}
        sale_id = start_sale(simulator_api, headers, "01JCPRODUCTSIMULATOR000000")["saleId"]
        _agree(simulator_api, headers, sale_id)
        link = simulator_api.client.post(
            f"{SALES_PATH}/{sale_id}/payment-links",
            headers={**headers, "Idempotency-Key": "logging-link-key-0001"},
        ).json()
        simulator_api.client.post(
            f"{SIMULATOR_PATH}/payments/{link['orderId']}/completed", headers=headers
        )
        simulator_api.client.get(f"{SALES_PATH}/{sale_id}/handoff", headers=headers)
        simulator_api.client.get(f"{SALES_PATH}/{sale_id}/payment-status", headers=headers)
    logged_text = render_log_records(caplog.records)
    assert "request completed" in logged_text
    for secret_text in (pairing["accessToken"], "Bearer", "Authorization", link["paymentUrl"]):
        assert secret_text not in logged_text
