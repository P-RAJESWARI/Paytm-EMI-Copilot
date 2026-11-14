"""SaleStatusBroadcaster: tells a shop's open live streams about its sales' committed statuses.

Fan-out is in-process: the registry of open streams lives in this one Python process, so the
API must run as a single uvicorn worker for every stream to hear every change (ADR at the
Layer 2 gate). A message carries only the sale id, its status and when it changed (rule 6).
"""

import asyncio
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import partial

from emi_copilot.domain.events import SaleStarted, SaleStatusChanged
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork


class SaleStatusFeedMessageKind(StrEnum):
    """What one message on a live stream means."""

    SALE_STATUS = "sale-status"
    """One sale now has this status."""

    RESYNC = "resync"
    """Messages were dropped because the stream fell behind; read the counter list again."""


@dataclass(frozen=True, slots=True)
class SaleStatusUpdate:
    """A sale's committed status and the moment it took it; nothing about the customer."""

    sale_id: str
    status: SaleStatus
    status_changed_at: datetime


@dataclass(frozen=True, slots=True)
class SaleStatusFeedMessage:
    """One message for a live stream: a status update, or a request to resynchronise."""

    kind: SaleStatusFeedMessageKind
    update: SaleStatusUpdate | None = None


RESYNC_MESSAGE = SaleStatusFeedMessage(SaleStatusFeedMessageKind.RESYNC)


class SaleStatusSubscription:
    """One open live stream of one shop: a bounded queue read on the event loop that opened it.

    Messages may be offered from any thread; they are handed to the loop, and only the loop
    touches the queue. When the queue is full, its backlog is dropped and replaced by a single
    resync message, so a slow reader costs bounded memory and still learns it missed something.
    """

    def __init__(
        self,
        merchant_id: str,
        event_loop: asyncio.AbstractEventLoop,
        maximum_queued_messages: int,
    ) -> None:
        """Keeps the shop it listens for, the loop that reads it and the queue bound."""
        self.merchant_id = merchant_id
        self._event_loop = event_loop
        self._queue: asyncio.Queue[SaleStatusFeedMessage] = asyncio.Queue(
            maxsize=maximum_queued_messages
        )

    def offer_from_any_thread(self, message: SaleStatusFeedMessage) -> None:
        """Hands a message to the reading loop; raises RuntimeError once that loop is closed."""
        self._event_loop.call_soon_threadsafe(self._enqueue_on_loop, message)

    def _enqueue_on_loop(self, message: SaleStatusFeedMessage) -> None:
        """Queues the message, or swaps a full backlog (and this message) for one resync."""
        if self._queue.full():
            while not self._queue.empty():
                self._queue.get_nowait()
            self._queue.put_nowait(RESYNC_MESSAGE)
            return
        self._queue.put_nowait(message)

    async def receive_message(self, timeout_in_seconds: float) -> SaleStatusFeedMessage | None:
        """Waits up to the timeout for the next message; None when nothing came in time."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout_in_seconds)
        except TimeoutError:
            return None


# Pattern: Observer. Sale services publish SaleStarted and SaleStatusChanged without knowing a
# live feed exists; this subscriber forwards them, after commit, to the owning shop's streams.
class SaleStatusBroadcaster:
    """Registry of open live streams per shop, fed by the event bus after each commit.

    Built once by the composition root and kept on the application components, never in a
    module global. Delivery waits for the publishing transaction to commit (call_after_commit),
    so a rolled-back change is never announced; only the owning shop's streams receive it.
    """

    def __init__(self, maximum_queued_messages_per_stream: int) -> None:
        """Starts with no open streams; each stream's queue holds at most the given messages."""
        if maximum_queued_messages_per_stream < 1:
            raise ValueError("A live stream must be able to queue at least one message.")
        self._maximum_queued_messages_per_stream = maximum_queued_messages_per_stream
        self._subscriptions_by_merchant_id: dict[str, set[SaleStatusSubscription]] = {}
        self._lock = threading.Lock()

    def subscribe_to(self, event_bus: DomainEventBus) -> None:
        """Listens for sales starting and changing status."""
        event_bus.subscribe(SaleStarted, self.schedule_sale_started)
        event_bus.subscribe(SaleStatusChanged, self.schedule_sale_status_changed)

    def schedule_sale_started(self, event: SaleStarted, unit_of_work: UnitOfWork) -> None:
        """Announces the new CHOOSING sale once the transaction that started it commits."""
        update = SaleStatusUpdate(event.sale_id, SaleStatus.CHOOSING, event.occurred_at)
        unit_of_work.call_after_commit(partial(self.broadcast, event.merchant_id, update))

    def schedule_sale_status_changed(
        self, event: SaleStatusChanged, unit_of_work: UnitOfWork
    ) -> None:
        """Announces the sale's new status once the transaction that moved it commits."""
        update = SaleStatusUpdate(event.sale_id, event.new_status, event.occurred_at)
        unit_of_work.call_after_commit(partial(self.broadcast, event.merchant_id, update))

    def open_subscription(self, merchant_id: str) -> SaleStatusSubscription:
        """Opens a stream for the shop on the running event loop; call it from async code."""
        subscription = SaleStatusSubscription(
            merchant_id, asyncio.get_running_loop(), self._maximum_queued_messages_per_stream
        )
        with self._lock:
            self._subscriptions_by_merchant_id.setdefault(merchant_id, set()).add(subscription)
        return subscription

    def close_subscription(self, subscription: SaleStatusSubscription) -> None:
        """Forgets a stream; closing one that is already closed does nothing."""
        with self._lock:
            subscriptions = self._subscriptions_by_merchant_id.get(subscription.merchant_id)
            if subscriptions is None:
                return
            subscriptions.discard(subscription)
            if not subscriptions:
                del self._subscriptions_by_merchant_id[subscription.merchant_id]

    def count_open_subscriptions(self, merchant_id: str) -> int:
        """Gives how many streams the shop has open now."""
        with self._lock:
            return len(self._subscriptions_by_merchant_id.get(merchant_id, ()))

    def broadcast(self, merchant_id: str, update: SaleStatusUpdate) -> None:
        """Offers the update to each of the shop's streams; one whose loop has closed is dropped."""
        with self._lock:
            subscriptions = tuple(self._subscriptions_by_merchant_id.get(merchant_id, ()))
        message = SaleStatusFeedMessage(SaleStatusFeedMessageKind.SALE_STATUS, update)
        for subscription in subscriptions:
            try:
                subscription.offer_from_any_thread(message)
            except RuntimeError:
                self.close_subscription(subscription)
