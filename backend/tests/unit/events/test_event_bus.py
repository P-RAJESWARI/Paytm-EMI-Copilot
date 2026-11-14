"""Tests for DomainEventBus: exact-type, in-order, synchronous delivery in the caller's unit."""

import pytest

from emi_copilot.domain.events import DomainEvent, PaymentLinkCreated, PaymentStatusChanged
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork
from tests.event_builders import build_every_domain_event, build_payment_status_changed
from tests.fakes.fake_unit_of_work import FakeUnitOfWork, InMemoryDatabase
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT


class SubscriberFailureError(Exception):
    """Stands in for any error a subscriber raises."""


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    """Gives a fake unit of work to pass along with each published event."""
    return FakeUnitOfWork(InMemoryDatabase(), FixedClock(CREATED_AT))


def test_publish_without_subscribers_does_nothing(unit_of_work: FakeUnitOfWork) -> None:
    """An event nobody listens to is simply dropped."""
    DomainEventBus().publish(build_payment_status_changed(), unit_of_work)


def test_publish_calls_handlers_of_the_exact_type_in_order_with_the_unit_of_work(
    unit_of_work: FakeUnitOfWork,
) -> None:
    """Every handler of the type runs, in subscription order, and gets the publisher's unit."""
    received_calls: list[tuple[str, DomainEvent, UnitOfWork]] = []
    event_bus = DomainEventBus()
    event_bus.subscribe(
        PaymentStatusChanged, lambda event, unit: received_calls.append(("first", event, unit))
    )
    event_bus.subscribe(
        PaymentStatusChanged, lambda event, unit: received_calls.append(("second", event, unit))
    )
    event_bus.subscribe(
        PaymentLinkCreated, lambda event, unit: received_calls.append(("other", event, unit))
    )
    event = build_payment_status_changed()
    event_bus.publish(event, unit_of_work)
    assert received_calls == [("first", event, unit_of_work), ("second", event, unit_of_work)]


def test_publish_lets_a_subscriber_error_reach_the_publisher(unit_of_work: FakeUnitOfWork) -> None:
    """A failing subscriber fails the use case, so its unit of work rolls back."""

    def fail(event: PaymentStatusChanged, unit: UnitOfWork) -> None:  # noqa: ARG001
        """Raises for every event, whatever it and the unit of work hold."""
        raise SubscriberFailureError

    event_bus = DomainEventBus()
    event_bus.subscribe(PaymentStatusChanged, fail)
    with pytest.raises(SubscriberFailureError):
        event_bus.publish(build_payment_status_changed(), unit_of_work)


def test_domain_events_are_immutable() -> None:
    """A published fact cannot be changed by a subscriber."""
    for event in build_every_domain_event():
        with pytest.raises(AttributeError):
            event.occurred_at = CREATED_AT  # type: ignore[misc]
