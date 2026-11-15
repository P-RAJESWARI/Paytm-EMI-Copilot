"""FunnelEventRecorder: STARTED, AGREED and PAID rows, in the publisher's unit of work only."""

import pytest

from emi_copilot.domain.events import CustomerBudgetConfirmed, CustomerPlansViewed, SaleStarted
from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.events.funnel_event_recorder import FunnelEventRecorder
from tests.event_builders import (
    SAMPLE_MERCHANT_ID,
    SAMPLE_SALE_ID,
    build_every_domain_event,
    build_sale_status_changed,
)
from tests.fakes.fake_unit_of_work import FakeUnitOfWorkFactory, InMemoryDatabase
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT

Status = SaleStatus


class SimulatedUseCaseFailureError(Exception):
    """Stands in for any error the sale service raises after publishing."""


@pytest.fixture
def unit_of_work_factory() -> FakeUnitOfWorkFactory:
    """Gives fake units of work on one shared in-memory database."""
    return FakeUnitOfWorkFactory(InMemoryDatabase(), FixedClock(CREATED_AT))


@pytest.fixture
def event_bus() -> DomainEventBus:
    """A bus with only the funnel recorder on it."""
    bus = DomainEventBus()
    FunnelEventRecorder(SequentialIdGenerator("01JCFUNNELID")).subscribe_to(bus)
    return bus


def recorded_stages(unit_of_work_factory: FakeUnitOfWorkFactory) -> list[FunnelStage]:
    """Lists the committed funnel stages, oldest first."""
    return [funnel_event.stage for funnel_event in unit_of_work_factory.database.funnel_events]


def test_sale_started_records_the_started_stage_at_the_event_moment(
    event_bus: DomainEventBus, unit_of_work_factory: FakeUnitOfWorkFactory
) -> None:
    """A started sale is counted once in "Started", with no budget."""
    started_event = next(
        event for event in build_every_domain_event() if isinstance(event, SaleStarted)
    )
    with unit_of_work_factory() as unit_of_work:
        event_bus.publish(started_event, unit_of_work)
    assert unit_of_work_factory.database.funnel_events == [
        FunnelEvent(
            id="01JCFUNNELID00000000000001",
            sale_id=started_event.sale_id,
            merchant_id=started_event.merchant_id,
            stage=FunnelStage.STARTED,
            occurred_at=CREATED_AT,
        )
    ]


@pytest.mark.parametrize(
    ("previous_status", "new_status", "expected_stages"),
    [
        (Status.CHOOSING, Status.READY_TO_PAY, [FunnelStage.AGREED]),
        (Status.READY_TO_PAY, Status.PAID, [FunnelStage.PAID]),
        (Status.PAYMENT_NOT_COMPLETED, Status.PAID, [FunnelStage.PAID]),
        (Status.PAYMENT_NOT_COMPLETED, Status.READY_TO_PAY, []),
        (Status.READY_TO_PAY, Status.PAYMENT_NOT_COMPLETED, []),
        (Status.CHOOSING, Status.EXPIRED, []),
    ],
)
def test_status_change_records_agreed_on_first_agreement_and_paid_on_payment(
    event_bus: DomainEventBus,
    unit_of_work_factory: FakeUnitOfWorkFactory,
    previous_status: SaleStatus,
    new_status: SaleStatus,
    expected_stages: list[FunnelStage],
) -> None:
    """A retried payment is not a second agreement; expiry and failures reach no stage."""
    with unit_of_work_factory() as unit_of_work:
        event_bus.publish(
            build_sale_status_changed(previous_status=previous_status, new_status=new_status),
            unit_of_work,
        )
    assert recorded_stages(unit_of_work_factory) == expected_stages


def test_funnel_row_is_discarded_when_the_unit_of_work_rolls_back(
    event_bus: DomainEventBus, unit_of_work_factory: FakeUnitOfWorkFactory
) -> None:
    """The funnel row lives and dies with the sale change that caused it."""

    def publish_then_fail() -> None:
        """Publishes an agreement, then fails before the unit can commit."""
        with unit_of_work_factory() as unit_of_work:
            event_bus.publish(build_sale_status_changed(), unit_of_work)
            raise SimulatedUseCaseFailureError

    with pytest.raises(SimulatedUseCaseFailureError):
        publish_then_fail()
    assert recorded_stages(unit_of_work_factory) == []


def build_budget_confirmed(monthly_budget_in_paise: int = 300_000) -> CustomerBudgetConfirmed:
    """The design customer confirming a ₹3,000 budget on the sample sale."""
    return CustomerBudgetConfirmed(
        occurred_at=CREATED_AT,
        sale_id=SAMPLE_SALE_ID,
        merchant_id=SAMPLE_MERCHANT_ID,
        monthly_budget_in_paise=monthly_budget_in_paise,
    )


def test_budget_confirmed_records_budget_told_with_the_budget(
    event_bus: DomainEventBus, unit_of_work_factory: FakeUnitOfWorkFactory
) -> None:
    """The first confirmed budget is kept on BUDGET_TOLD for the report's budget buckets."""
    with unit_of_work_factory() as unit_of_work:
        event_bus.publish(build_budget_confirmed(), unit_of_work)
    assert unit_of_work_factory.database.funnel_events == [
        FunnelEvent(
            id="01JCFUNNELID00000000000001",
            sale_id=SAMPLE_SALE_ID,
            merchant_id=SAMPLE_MERCHANT_ID,
            stage=FunnelStage.BUDGET_TOLD,
            occurred_at=CREATED_AT,
            monthly_budget=Money.from_rupees(3000),
        )
    ]


def test_budget_confirmed_again_keeps_the_first_budget_and_does_not_fail(
    event_bus: DomainEventBus, unit_of_work_factory: FakeUnitOfWorkFactory
) -> None:
    """A changed budget (₹30,000 misheard, then ₹3,000) is told once per sale, never failing."""
    for monthly_budget_in_paise in (3_000_000, 300_000):
        with unit_of_work_factory() as unit_of_work:
            event_bus.publish(build_budget_confirmed(monthly_budget_in_paise), unit_of_work)
    (budget_told,) = unit_of_work_factory.database.funnel_events
    assert budget_told.monthly_budget == Money.from_rupees(30000)


def test_plans_viewed_records_plans_viewed_once_per_sale(
    event_bus: DomainEventBus, unit_of_work_factory: FakeUnitOfWorkFactory
) -> None:
    """Viewing the plans twice counts the sale once in "Viewed plans"."""
    for _ in range(2):
        with unit_of_work_factory() as unit_of_work:
            event_bus.publish(
                CustomerPlansViewed(
                    occurred_at=CREATED_AT,
                    sale_id=SAMPLE_SALE_ID,
                    merchant_id=SAMPLE_MERCHANT_ID,
                ),
                unit_of_work,
            )
    assert recorded_stages(unit_of_work_factory) == [FunnelStage.PLANS_VIEWED]
