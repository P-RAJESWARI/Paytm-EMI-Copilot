"""SaleStatusFeedService: messages as they come, heartbeats when quiet, an end at token expiry."""

import asyncio
from datetime import timedelta

from emi_copilot.domain.sales import SaleStatus
from emi_copilot.events.sale_status_broadcaster import (
    SaleStatusBroadcaster,
    SaleStatusFeedMessage,
    SaleStatusFeedMessageKind,
    SaleStatusUpdate,
)
from emi_copilot.services.sale_status_feed_service import SaleStatusFeedService
from tests.fixed_clock import FixedClock
from tests.merchant_builders import MERCHANT_ID, PAIRED_AT
from tests.sale_builders import SALE_ID
from tests.unit.services.sale_service_wiring import PRINCIPAL

QUICK_HEARTBEAT = timedelta(milliseconds=20)
READY_UPDATE = SaleStatusUpdate(SALE_ID, SaleStatus.READY_TO_PAY, PAIRED_AT)


def _wire(clock: FixedClock) -> tuple[SaleStatusBroadcaster, SaleStatusFeedService]:
    """A broadcaster and the feed service on it with a 20 ms heartbeat."""
    broadcaster = SaleStatusBroadcaster(maximum_queued_messages_per_stream=10)
    return broadcaster, SaleStatusFeedService(broadcaster, clock, QUICK_HEARTBEAT)


def test_feed_gives_a_heartbeat_when_quiet_then_the_update_then_ends_at_token_expiry() -> None:
    """None stands for one quiet interval; past the token's expiry the feed closes itself."""
    clock = FixedClock(PAIRED_AT)
    broadcaster, feed_service = _wire(clock)

    async def scenario() -> list[SaleStatusFeedMessage | None]:
        """Reads the feed: a heartbeat, an update, then the end after the clock passes expiry."""
        feed = feed_service.open_feed(PRINCIPAL)
        items: list[SaleStatusFeedMessage | None] = []
        async for item in feed.follow():
            items.append(item)
            if len(items) == 1:
                broadcaster.broadcast(MERCHANT_ID, READY_UPDATE)
            elif len(items) == 2:
                clock.advance(timedelta(hours=12))
        return items

    assert asyncio.run(scenario()) == [
        None,
        SaleStatusFeedMessage(SaleStatusFeedMessageKind.SALE_STATUS, READY_UPDATE),
    ]
    assert broadcaster.count_open_subscriptions(MERCHANT_ID) == 0


def test_feed_whose_token_expires_during_a_quiet_wait_ends_without_a_heartbeat() -> None:
    """Expiry inside the wait ends the stream instead of sending one more keep-alive."""
    clock = FixedClock(PAIRED_AT)
    _, feed_service = _wire(clock)

    async def scenario() -> list[SaleStatusFeedMessage | None]:
        """Moves the clock past expiry while the feed waits, then collects what it yielded."""
        feed = feed_service.open_feed(PRINCIPAL)
        asyncio.get_running_loop().call_later(0.005, clock.advance, timedelta(hours=12))
        return [item async for item in feed.follow()]

    assert asyncio.run(scenario()) == []


def test_feed_waits_no_longer_than_the_time_left_on_the_token() -> None:
    """With 10 ms left and a long heartbeat, the first wait is cut short at the expiry."""
    clock = FixedClock(PRINCIPAL.access_expires_at - timedelta(milliseconds=10))
    broadcaster = SaleStatusBroadcaster(maximum_queued_messages_per_stream=10)
    feed_service = SaleStatusFeedService(broadcaster, clock, timedelta(minutes=5))

    async def scenario() -> tuple[SaleStatusFeedMessage | None, float]:
        """Times the first quiet wait of the feed."""
        feed = feed_service.open_feed(PRINCIPAL)
        started_at = asyncio.get_running_loop().time()
        stream = feed.follow()
        first_item = await anext(stream)
        waited_in_seconds = asyncio.get_running_loop().time() - started_at
        clock.advance(timedelta(seconds=1))
        assert [item async for item in stream] == []
        return first_item, waited_in_seconds

    first_item, waited_in_seconds = asyncio.run(scenario())
    assert first_item is None
    assert waited_in_seconds < 1


def test_closing_a_feed_before_it_is_read_forgets_its_subscription() -> None:
    """The response's background close covers a client that leaves before the first frame."""
    clock = FixedClock(PAIRED_AT)
    broadcaster, feed_service = _wire(clock)

    async def open_and_close() -> None:
        """Opens a feed and closes it twice without reading it."""
        feed = feed_service.open_feed(PRINCIPAL)
        assert broadcaster.count_open_subscriptions(MERCHANT_ID) == 1
        feed.close()
        feed.close()

    asyncio.run(open_and_close())
    assert broadcaster.count_open_subscriptions(MERCHANT_ID) == 0
