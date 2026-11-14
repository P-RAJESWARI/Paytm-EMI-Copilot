"""SaleStatusFeedService: one shop's live stream of sale statuses, until its device token expires.

Fan-out is in-process (SaleStatusBroadcaster), so the API must run as a single uvicorn worker
for every stream to hear every change; an ADR records this at the Layer 2 gate.
"""

from collections.abc import AsyncIterator
from datetime import datetime, timedelta

from emi_copilot.core.clock import Clock
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.events.sale_status_broadcaster import (
    SaleStatusBroadcaster,
    SaleStatusFeedMessage,
    SaleStatusSubscription,
)


class SaleStatusFeed:
    """An open stream: committed status messages, with None for each quiet heartbeat interval.

    It ends at the device token's expiry, so a stream never outlives the sign-in that opened it;
    the client then pairs again and reconnects. Closing it (also when the client disconnects)
    forgets the subscription; closing twice is harmless.
    """

    def __init__(
        self,
        broadcaster: SaleStatusBroadcaster,
        subscription: SaleStatusSubscription,
        clock: Clock,
        heartbeat_interval: timedelta,
        ends_at: datetime,
    ) -> None:
        """Keeps the open subscription, the clock, the heartbeat interval and the end moment."""
        self._broadcaster = broadcaster
        self._subscription = subscription
        self._clock = clock
        self._heartbeat_interval = heartbeat_interval
        self._ends_at = ends_at

    async def follow(self) -> AsyncIterator[SaleStatusFeedMessage | None]:
        """Yields each message as it comes, or None after a heartbeat interval without one."""
        try:
            while self._clock.now() < self._ends_at:
                seconds_left = (self._ends_at - self._clock.now()).total_seconds()
                message = await self._subscription.receive_message(
                    min(self._heartbeat_interval.total_seconds(), seconds_left)
                )
                if message is not None:
                    yield message
                elif self._clock.now() < self._ends_at:
                    yield None
        finally:
            self.close()

    def close(self) -> None:
        """Forgets the subscription, so no more messages are queued for this stream."""
        self._broadcaster.close_subscription(self._subscription)


class SaleStatusFeedService:
    """Opens live streams for signed-in shops; each hears only its own shop's sales (rule 6)."""

    def __init__(
        self, broadcaster: SaleStatusBroadcaster, clock: Clock, heartbeat_interval: timedelta
    ) -> None:
        """Keeps the startup broadcaster, the clock and how often a quiet stream is pinged."""
        self._broadcaster = broadcaster
        self._clock = clock
        self._heartbeat_interval = heartbeat_interval

    def open_feed(self, principal: MerchantPrincipal) -> SaleStatusFeed:
        """Subscribes now, before the response starts, so no change after this call is missed.

        Call it from async code: the subscription belongs to the running event loop.
        """
        subscription = self._broadcaster.open_subscription(principal.merchant_id)
        return SaleStatusFeed(
            self._broadcaster,
            subscription,
            self._clock,
            self._heartbeat_interval,
            principal.access_expires_at,
        )
