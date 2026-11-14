"""A kit of fakes every service test builds its service from: no database and no network."""

from dataclasses import dataclass

import pytest

from emi_copilot.domain.payments import AuditEvent, AuditEventType, PaymentAttempt
from emi_copilot.events.audit_subscriber import AuditSubscriber
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.events.funnel_event_recorder import FunnelEventRecorder
from emi_copilot.events.sale_payment_outcome_subscriber import SalePaymentOutcomeSubscriber
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.fake_unit_of_work import FakeUnitOfWorkFactory, InMemoryDatabase
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT


@dataclass
class ServiceTestKit:
    """The fakes a service is wired with, and helpers to read what was committed."""

    clock: FixedClock
    id_generator: SequentialIdGenerator
    database: InMemoryDatabase
    unit_of_work_factory: FakeUnitOfWorkFactory
    payment_gateway: FakePaymentGateway
    event_bus: DomainEventBus

    def store_attempt(self, payment_attempt: PaymentAttempt) -> None:
        """Puts an attempt straight into the committed state, as an earlier request would have."""
        self.database.payment_attempts_by_id[payment_attempt.id] = payment_attempt

    def only_attempt(self) -> PaymentAttempt:
        """Gives the single committed attempt; fails the test if there is not exactly one."""
        (payment_attempt,) = self.database.payment_attempts_by_id.values()
        return payment_attempt

    def audit_event_types(self) -> list[AuditEventType]:
        """Lists the types of every committed audit event, oldest first."""
        return [audit_event.event_type for audit_event in self.database.audit_events]

    def last_audit_event(self) -> AuditEvent:
        """Gives the newest committed audit event."""
        return self.database.audit_events[-1]


@pytest.fixture
def kit() -> ServiceTestKit:
    """Wires fresh fakes, with the subscribers on the bus in the composition root's order."""
    clock = FixedClock(CREATED_AT)
    database = InMemoryDatabase()
    event_bus = DomainEventBus()
    AuditSubscriber(SequentialIdGenerator("01JCAUDITID"), lambda: None).subscribe_to(event_bus)
    FunnelEventRecorder(SequentialIdGenerator("01JCFUNNELID")).subscribe_to(event_bus)
    SalePaymentOutcomeSubscriber(event_bus).subscribe()
    return ServiceTestKit(
        clock=clock,
        id_generator=SequentialIdGenerator(),
        database=database,
        unit_of_work_factory=FakeUnitOfWorkFactory(database, clock),
        payment_gateway=FakePaymentGateway(),
        event_bus=event_bus,
    )
