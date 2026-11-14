"""GET /api/v1/sales/events on PostgreSQL: live, committed, own shop only, ends at token expiry."""

import asyncio
import json
from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.api.dependencies import ApplicationComponents
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import GatewayPaymentStatus
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import ApiHarness, open_api_harness
from tests.integration.api.asgi_event_stream import AsgiEventStream
from tests.integration.api.sale_api_helpers import (
    SALES_PATH,
    TwoShops,
    agree_to_offer_in_the_service,
    start_sale,
    store_and_pair_two_shops,
)

pytestmark = pytest.mark.integration

EVENTS_PATH = f"{SALES_PATH}/events"
QUICK_HEARTBEAT_IN_SECONDS = 0.05
# The first shop that store_and_pair_two_shops stores.
FIRST_SHOP_MERCHANT_ID = "01JCMERCHANTSALES000000001"


@pytest.fixture
def streaming_api(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
) -> Iterator[ApiHarness]:
    """Runs the application with a 50 ms heartbeat, so quiet streams are quick to observe."""
    settings = ApplicationSettings(
        sale_event_stream_heartbeat_interval_in_seconds=QUICK_HEARTBEAT_IN_SECONDS
    )
    with open_api_harness(session_factory, fixed_clock, mock_gateway, settings) as harness:
        yield harness


@pytest.fixture
def streaming_shops(streaming_api: ApiHarness) -> TwoShops:
    """Two paired shops with the M2 catalogue on the quick-heartbeat application."""
    return store_and_pair_two_shops(streaming_api)


def _open_stream(harness: ApiHarness, headers: dict[str, str]) -> AsgiEventStream:
    """Prepares a stream request on the running application."""
    return AsgiEventStream(harness.client.app, EVENTS_PATH, headers)


def _read_components(harness: ApiHarness) -> ApplicationComponents:
    """Gives the components the application built at startup."""
    components: ApplicationComponents = harness.client.app.state.application_components  # type: ignore[attr-defined]
    return components


def _parse_sale_status_frame(frame: str | None) -> dict[str, object]:
    """Checks a frame is a sale-status event and gives its JSON data."""
    assert frame is not None
    event_line, data_line = frame.split("\n")
    assert event_line == "event: sale-status"
    data: dict[str, object] = json.loads(data_line.removeprefix("data: "))
    return data


def test_agreed_plan_reaches_the_owning_shops_stream_as_ready_to_pay(
    streaming_api: ApiHarness,
    streaming_shops: TwoShops,
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """A new sale shows as CHOOSING, the agreement as READY_TO_PAY; the other shop hears nothing."""

    async def scenario() -> tuple[list[dict[str, object]], str | None]:
        """Opens both shops' streams, starts and agrees a sale for the first shop, reads both."""
        own_stream = _open_stream(streaming_api, streaming_shops.first_shop_headers)
        other_stream = _open_stream(streaming_api, streaming_shops.second_shop_headers)
        await own_stream.open()
        await other_stream.open()
        sale = await asyncio.to_thread(
            start_sale, streaming_api, streaming_shops.first_shop_headers
        )
        await asyncio.to_thread(
            agree_to_offer_in_the_service, streaming_api, mock_gateway, sale["saleId"]
        )
        own_events = [
            _parse_sale_status_frame(await own_stream.read_frame_other_than_heartbeat())
            for _ in range(2)
        ]
        other_frame = await other_stream.read_frame()
        await own_stream.close()
        await other_stream.close()
        assert own_stream.status_code == 200
        assert own_stream.response_headers["content-type"].startswith("text/event-stream")
        assert own_stream.response_headers["cache-control"] == "no-store"
        return own_events, other_frame

    own_events, other_frame = asyncio.run(scenario())
    assert [event["status"] for event in own_events] == ["CHOOSING", "READY_TO_PAY"]
    assert {frozenset(event) for event in own_events} == {
        frozenset({"saleId", "status", "statusChangedAt"})
    }
    assert other_frame == ": heartbeat"


def test_verified_paid_webhook_is_announced_live_as_paid(
    streaming_api: ApiHarness,
    streaming_shops: TwoShops,
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """The gateway's signed report, through the real webhook endpoint, reaches the tablet."""
    headers = streaming_shops.first_shop_headers
    sale_id = start_sale(streaming_api, headers)["saleId"]
    agree_to_offer_in_the_service(streaming_api, mock_gateway, sale_id)
    link_response = streaming_api.client.post(
        f"{SALES_PATH}/{sale_id}/payment-links",
        headers={**headers, "Idempotency-Key": "stream-link-key-0001"},
    )
    notification = mock_gateway.build_signed_notification(
        link_response.json()["orderId"],
        GatewayPaymentStatus.PAID,
        "mock-transaction-0001",
        Money.from_paise(2_200_000),
    )

    async def scenario() -> dict[str, object]:
        """Opens the stream, delivers the webhook and reads the next event."""
        stream = _open_stream(streaming_api, headers)
        await stream.open()
        webhook_response = await asyncio.to_thread(
            streaming_api.client.post,
            "/api/v1/webhooks/paytm",
            data=dict(notification.received_fields),
        )
        assert webhook_response.status_code == 202
        event = _parse_sale_status_frame(await stream.read_frame_other_than_heartbeat())
        await stream.close()
        return event

    assert asyncio.run(scenario())["status"] == "PAID"


def test_quiet_stream_sends_heartbeats_and_ends_once_the_token_expires(
    streaming_api: ApiHarness, streaming_shops: TwoShops
) -> None:
    """Heartbeat comments keep it open; past the 12-hour token the body ends by itself."""

    async def scenario() -> tuple[list[str | None], int]:
        """Reads two heartbeats, moves the clock past expiry, and reads to the end."""
        stream = _open_stream(streaming_api, streaming_shops.first_shop_headers)
        await stream.open()
        frames = [await stream.read_frame(), await stream.read_frame()]
        streaming_api.clock.advance(timedelta(hours=12))
        while (frame := await stream.read_frame()) is not None:
            frames.append(frame)
        await stream.close()
        broadcaster = _read_components(streaming_api).sale_status_broadcaster
        return frames, broadcaster.count_open_subscriptions(FIRST_SHOP_MERCHANT_ID)

    frames, open_subscription_count = asyncio.run(scenario())
    assert frames[:2] == [": heartbeat", ": heartbeat"]
    assert set(frames) == {": heartbeat"}
    assert open_subscription_count == 0


def test_client_disconnect_closes_the_shops_subscription(
    streaming_api: ApiHarness, streaming_shops: TwoShops
) -> None:
    """A closed tab leaves nothing behind in the broadcaster."""
    broadcaster = _read_components(streaming_api).sale_status_broadcaster
    merchant_id = FIRST_SHOP_MERCHANT_ID

    async def scenario() -> tuple[int, int]:
        """Opens a stream, counts the subscription, disconnects and counts again."""
        stream = _open_stream(streaming_api, streaming_shops.first_shop_headers)
        await stream.open()
        open_count = broadcaster.count_open_subscriptions(merchant_id)
        await stream.close()
        return open_count, broadcaster.count_open_subscriptions(merchant_id)

    assert asyncio.run(scenario()) == (1, 0)


def test_stream_without_a_token_answers_401_problem(streaming_api: ApiHarness) -> None:
    """The live feed is a merchant endpoint like every other."""
    response = streaming_api.client.get(EVENTS_PATH)
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "MERCHANT_AUTHENTICATION_REQUIRED"
