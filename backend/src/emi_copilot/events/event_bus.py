"""DomainEventBus: synchronous, in-process delivery of domain events to their subscribers."""

from collections.abc import Callable
from typing import cast

from emi_copilot.domain.events import DomainEvent
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork

type DomainEventHandler[EventType: DomainEvent] = Callable[[EventType, UnitOfWork], None]
"""A subscriber callback; it receives the publisher's active unit of work to write in."""


# Pattern: Observer. Services announce what happened; audit (and later the merchant status feed)
# subscribe without the services knowing about them.
class DomainEventBus:
    """Calls every handler subscribed to an event's exact type, in subscription order.

    Delivery is synchronous and inside the publisher's unit of work, so a subscriber's writes
    commit or roll back together with the business write, and a subscriber that raises makes
    the whole use case fail. There is no global instance: the composition root builds one and
    subscribes every handler at startup, before any event is published.
    """

    def __init__(self) -> None:
        """Starts with no subscribers."""
        self._handlers_by_event_type: dict[
            type[DomainEvent], list[DomainEventHandler[DomainEvent]]
        ] = {}

    def subscribe[EventType: DomainEvent](
        self, event_type: type[EventType], handler: DomainEventHandler[EventType]
    ) -> None:
        """Registers a handler for one event type; it runs for events of exactly that type."""
        # Safe: publish passes a handler only events whose exact type it was registered for.
        handler_for_any_event = cast("DomainEventHandler[DomainEvent]", handler)
        self._handlers_by_event_type.setdefault(event_type, []).append(handler_for_any_event)

    def publish(self, event: DomainEvent, unit_of_work: UnitOfWork) -> None:
        """Delivers the event to its handlers now, in the given unit of work; errors propagate."""
        for handler in tuple(self._handlers_by_event_type.get(type(event), ())):
            handler(event, unit_of_work)
