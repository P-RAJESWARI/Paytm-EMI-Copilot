"""Tests for SaleStatusBroadcaster: after commit only, owning shop only, bounded per stream."""

import asyncio
import threading

import pytest

from emi_copilot.api.dependencies import build_event_bus
from emi_copilot.domain.events import SaleStarted, SaleStatusChanged
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.events.sale_status_broadcaster import (
    RESYNC_MESSAGE,
    SaleStatusBroadcaster,
    SaleStatusFeedMessage,
    SaleStatusFeedMessageKind,
    SaleStatusSubscription,
    SaleStatusUpdate,
)
from tests.fakes.fake_unit_of_work import FakeUnitOfWorkFactory, InMemoryDatabase
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.merchant_builders import MERCHANT_ID, OTHER_MERCHANT_ID
from tests.payment_builders import CREATED_AT
from tests.sale_builders import SALE_ID

# Long enough for a message already handed to the loop, short enough to keep the suite quick.
SHORT_WAIT_IN_SECONDS = 0.05


class SimulatedUseCaseFailureError(Exception):
    """Stands in for any error a service raises after publishing inside a unit of work."""


def _build_status_changed(merchant_id: str = MERCHANT_ID) -> SaleStatusChanged:
    """The shop's sale moving from CHOOSING to READY_TO_PAY."""
    return SaleStatusChanged(
        occurred_at=CREATED_AT,
        sale_id=SALE_ID,
        merchant_id=merchant_id,
        previous_status=SaleStatus.CHOOSING,
        new_status=SaleStatus.READY_TO_PAY,
        chosen_offer_id="offer-plan-a",
        payment_attempt_id=None,
    )


def _ready_to_pay_message() -> SaleStatusFeedMessage:
    """The message a stream receives for _build_status_changed."""
    return SaleStatusFeedMessage(
        SaleStatusFeedMessageKind.SALE_STATUS,
        SaleStatusUpdate(SALE_ID, SaleStatus.READY_TO_PAY, CREATED_AT),
    )


def _wire() -> tuple[SaleStatusBroadcaster, DomainEventBus, FakeUnitOfWorkFactory]:
    """A broadcaster listening on a fresh bus, and fake units of work to publish in."""
    broadcaster = SaleStatusBroadcaster(maximum_queued_messages_per_stream=2)
    event_bus = DomainEventBus()
    broadcaster.subscribe_to(event_bus)
    return broadcaster, event_bus, FakeUnitOfWorkFactory(InMemoryDatabase(), FixedClock(CREATED_AT))


def test_committed_status_change_reaches_only_the_owning_shops_streams() -> None:
    """The shop's stream gets the update; another shop's stream gets nothing."""
    broadcaster, event_bus, unit_of_work_factory = _wire()

    async def scenario() -> tuple[SaleStatusFeedMessage | None, SaleStatusFeedMessage | None]:
        """Opens one stream per shop, commits a change for the first shop and reads both."""
        own_stream = broadcaster.open_subscription(MERCHANT_ID)
        other_stream = broadcaster.open_subscription(OTHER_MERCHANT_ID)
        with unit_of_work_factory() as unit_of_work:
            event_bus.publish(_build_status_changed(), unit_of_work)
        return (
            await own_stream.receive_message(SHORT_WAIT_IN_SECONDS),
            await other_stream.receive_message(SHORT_WAIT_IN_SECONDS),
        )

    assert asyncio.run(scenario()) == (_ready_to_pay_message(), None)


def test_sale_started_is_announced_as_choosing_at_its_start() -> None:
    """A new sale appears on the shop's live list as CHOOSING."""
    broadcaster, event_bus, unit_of_work_factory = _wire()

    async def scenario() -> SaleStatusFeedMessage | None:
        """Opens a stream, commits a sale start and reads the stream."""
        stream = broadcaster.open_subscription(MERCHANT_ID)
        with unit_of_work_factory() as unit_of_work:
            event_bus.publish(
                SaleStarted(
                    occurred_at=CREATED_AT,
                    sale_id=SALE_ID,
                    merchant_id=MERCHANT_ID,
                    product_id="01JCPRODUCT000000000000001",
                    price_in_paise=2_200_000,
                ),
                unit_of_work,
            )
        return await stream.receive_message(SHORT_WAIT_IN_SECONDS)

    assert asyncio.run(scenario()) == SaleStatusFeedMessage(
        SaleStatusFeedMessageKind.SALE_STATUS,
        SaleStatusUpdate(SALE_ID, SaleStatus.CHOOSING, CREATED_AT),
    )


def test_rolled_back_status_change_is_never_announced() -> None:
    """A change whose transaction fails sends nothing to any stream."""
    broadcaster, event_bus, unit_of_work_factory = _wire()

    def publish_then_fail() -> None:
        """Publishes the change, then fails before the unit of work commits."""
        with unit_of_work_factory() as unit_of_work:
            event_bus.publish(_build_status_changed(), unit_of_work)
            raise SimulatedUseCaseFailureError

    async def scenario() -> SaleStatusFeedMessage | None:
        """Opens a stream, fails a transaction that published, and reads the stream."""
        stream = broadcaster.open_subscription(MERCHANT_ID)
        with pytest.raises(SimulatedUseCaseFailureError):
            publish_then_fail()
        return await stream.receive_message(SHORT_WAIT_IN_SECONDS)

    assert asyncio.run(scenario()) is None


def test_slow_stream_keeps_a_bounded_queue_and_is_told_to_resync() -> None:
    """Past the bound, the backlog is dropped for one resync, then new updates queue again."""
    broadcaster, _, _ = _wire()
    update = SaleStatusUpdate(SALE_ID, SaleStatus.READY_TO_PAY, CREATED_AT)

    async def scenario() -> list[SaleStatusFeedMessage | None]:
        """Offers four updates to a stream that holds two, then drains it."""
        stream = broadcaster.open_subscription(MERCHANT_ID)
        for _ in range(4):
            broadcaster.broadcast(MERCHANT_ID, update)
        await asyncio.sleep(0)
        return [await stream.receive_message(SHORT_WAIT_IN_SECONDS) for _ in range(3)]

    assert asyncio.run(scenario()) == [RESYNC_MESSAGE, _ready_to_pay_message(), None]


def test_update_committed_on_a_worker_thread_reaches_the_streams_event_loop() -> None:
    """Sync endpoints commit on worker threads; the message is handed to the loop safely."""
    broadcaster, _, _ = _wire()
    update = SaleStatusUpdate(SALE_ID, SaleStatus.READY_TO_PAY, CREATED_AT)

    async def scenario() -> tuple[SaleStatusFeedMessage | None, bool]:
        """Broadcasts from another thread while the loop waits on the stream."""
        stream = broadcaster.open_subscription(MERCHANT_ID)
        loop_thread_id = threading.get_ident()
        broadcasting_thread_ids: list[int] = []

        def broadcast_from_worker() -> None:
            """Broadcasts, remembering which thread did it."""
            broadcasting_thread_ids.append(threading.get_ident())
            broadcaster.broadcast(MERCHANT_ID, update)

        worker = threading.Thread(target=broadcast_from_worker)
        worker.start()
        message = await stream.receive_message(1.0)
        worker.join()
        return message, broadcasting_thread_ids != [loop_thread_id]

    assert asyncio.run(scenario()) == (_ready_to_pay_message(), True)


def test_stream_whose_event_loop_has_closed_is_dropped_on_the_next_broadcast() -> None:
    """A stream left behind by a finished loop cannot block or break later broadcasts."""
    broadcaster, _, _ = _wire()

    async def open_stream() -> SaleStatusSubscription:
        """Opens a stream on a loop that ends when this coroutine returns."""
        return broadcaster.open_subscription(MERCHANT_ID)

    asyncio.run(open_stream())
    assert broadcaster.count_open_subscriptions(MERCHANT_ID) == 1
    broadcaster.broadcast(
        MERCHANT_ID, SaleStatusUpdate(SALE_ID, SaleStatus.READY_TO_PAY, CREATED_AT)
    )
    assert broadcaster.count_open_subscriptions(MERCHANT_ID) == 0


def test_closing_a_stream_twice_and_broadcasting_to_nobody_do_nothing() -> None:
    """Closing is idempotent, and a shop with no streams costs nothing."""
    broadcaster, _, _ = _wire()

    async def open_two_and_close_one_twice() -> None:
        """Opens two streams for the shop and closes the first one twice."""
        first_stream = broadcaster.open_subscription(MERCHANT_ID)
        broadcaster.open_subscription(MERCHANT_ID)
        broadcaster.close_subscription(first_stream)
        broadcaster.close_subscription(first_stream)
        assert broadcaster.count_open_subscriptions(MERCHANT_ID) == 1

    asyncio.run(open_two_and_close_one_twice())
    broadcaster.broadcast(OTHER_MERCHANT_ID, SaleStatusUpdate(SALE_ID, SaleStatus.PAID, CREATED_AT))
    assert broadcaster.count_open_subscriptions(OTHER_MERCHANT_ID) == 0


def test_closing_the_last_stream_forgets_the_shop() -> None:
    """A closed stream is not counted, and closing again after the shop is gone is safe."""
    broadcaster, _, _ = _wire()

    async def open_and_close() -> None:
        """Opens one stream and closes it twice."""
        stream = broadcaster.open_subscription(MERCHANT_ID)
        broadcaster.close_subscription(stream)
        broadcaster.close_subscription(stream)

    asyncio.run(open_and_close())
    assert broadcaster.count_open_subscriptions(MERCHANT_ID) == 0


def test_broadcaster_refuses_a_queue_bound_below_one() -> None:
    """Every stream must be able to hold at least one message."""
    with pytest.raises(ValueError, match="at least one message"):
        SaleStatusBroadcaster(maximum_queued_messages_per_stream=0)


def test_composition_bus_feeds_the_broadcaster_after_audit_and_funnel_rows() -> None:
    """On the startup bus the broadcaster is subscribed last, and the rows still commit."""
    broadcaster = SaleStatusBroadcaster(maximum_queued_messages_per_stream=2)
    event_bus = build_event_bus(SequentialIdGenerator(), broadcaster)
    database = InMemoryDatabase()
    unit_of_work_factory = FakeUnitOfWorkFactory(database, FixedClock(CREATED_AT))

    async def scenario() -> SaleStatusFeedMessage | None:
        """Opens a stream, commits an agreement on the composition bus and reads the stream."""
        stream = broadcaster.open_subscription(MERCHANT_ID)
        with unit_of_work_factory() as unit_of_work:
            event_bus.publish(_build_status_changed(), unit_of_work)
        return await stream.receive_message(SHORT_WAIT_IN_SECONDS)

    assert asyncio.run(scenario()) == _ready_to_pay_message()
    assert len(database.audit_events) == 1
    assert len(database.funnel_events) == 1
