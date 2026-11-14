"""Integration tests for the append-only FunnelEventRepository and its database guards."""

from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.repositories.funnel_event_repository import FunnelEventRepository
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.fixed_clock import FixedClock
from tests.merchant_builders import build_catalogue_product, build_merchant
from tests.sale_builders import SALE_ID, SALE_STARTED_AT, build_funnel_event, build_sale

pytestmark = pytest.mark.integration


def store_sample_sale(session_factory: sessionmaker[Session], fixed_clock: FixedClock) -> None:
    """Commits the sample shop, its product and the sample sale the events refer to."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.merchants.add(build_merchant())
        unit_of_work.products.add(build_catalogue_product())
        unit_of_work.sales.add(build_sale())


def append_in_one_unit_of_work(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock, *events: FunnelEvent
) -> None:
    """Appends the events in one unit of work, which rolls back if any insert fails."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        for funnel_event in events:
            unit_of_work.funnel_events.append(funnel_event)


@pytest.fixture
def unit_of_work(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> Iterator[SqlAlchemyUnitOfWork]:
    """Stores the sample sale, then opens one unit of work for the test."""
    store_sample_sale(session_factory, fixed_clock)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as opened_unit_of_work:
        yield opened_unit_of_work


def test_funnel_event_repository_public_api_is_append_and_read_only() -> None:
    """No update or delete path exists on the funnel (security section 9)."""
    public_names = {name for name in dir(FunnelEventRepository) if not name.startswith("_")}
    assert public_names == {"append", "list_for_sale"}


def test_append_then_list_for_sale_returns_events_oldest_first_with_the_budget(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Stages come back unchanged and in order; the budget round-trips as integer paise."""
    started = build_funnel_event()
    budget_told = build_funnel_event(
        id="01JCFUNNELEVENT00000000002",
        stage=FunnelStage.BUDGET_TOLD,
        occurred_at=SALE_STARTED_AT + timedelta(minutes=1),
        monthly_budget=Money.from_rupees("3000"),
    )
    unit_of_work.funnel_events.append(budget_told)
    unit_of_work.funnel_events.append(started)
    assert unit_of_work.funnel_events.list_for_sale(SALE_ID) == (started, budget_told)
    assert unit_of_work.funnel_events.list_for_sale("01JCSALE000000000000000099") == ()


def test_database_refuses_a_second_event_for_the_same_sale_and_stage(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Each sale reaches each stage at most once, so funnel counts cannot double."""
    store_sample_sale(session_factory, fixed_clock)
    with pytest.raises(IntegrityError, match="uq_funnel_event_sale_id_stage"):
        append_in_one_unit_of_work(
            session_factory,
            fixed_clock,
            build_funnel_event(),
            build_funnel_event(id="01JCFUNNELEVENT00000000002"),
        )


@pytest.mark.parametrize(
    "insert_statement",
    [
        "INSERT INTO funnel_event VALUES ('01JCFUNNELRAW0000000000001', :sale_id, :merchant_id,"
        " 'STARTED', now(), 300000, now())",
        "INSERT INTO funnel_event VALUES ('01JCFUNNELRAW0000000000001', :sale_id, :merchant_id,"
        " 'BUDGET_TOLD', now(), NULL, now())",
        "INSERT INTO funnel_event VALUES ('01JCFUNNELRAW0000000000001', :sale_id, :merchant_id,"
        " 'BUDGET_TOLD', now(), 0, now())",
    ],
    ids=["budget-on-started", "budget-told-without-amount", "zero-budget"],
)
def test_database_keeps_a_positive_budget_on_budget_told_only(
    unit_of_work: SqlAlchemyUnitOfWork, database_connection: Connection, insert_statement: str
) -> None:
    """The CHECK constraints refuse a budget anywhere else, a missing one and a zero one."""
    sample_sale = build_sale()
    with pytest.raises(IntegrityError, match="ck_funnel_event"), database_connection.begin_nested():
        database_connection.execute(
            text(insert_statement),
            {"sale_id": sample_sale.id, "merchant_id": sample_sale.merchant_id},
        )
    assert unit_of_work.funnel_events.list_for_sale(SALE_ID) == ()


@pytest.mark.parametrize(
    "modifying_statement",
    [
        "UPDATE funnel_event SET stage = 'PAID' WHERE id = :id",
        "DELETE FROM funnel_event WHERE id = :id",
        "TRUNCATE funnel_event",
    ],
)
def test_raw_sql_modifying_funnel_event_is_rejected_by_trigger(
    unit_of_work: SqlAlchemyUnitOfWork, database_connection: Connection, modifying_statement: str
) -> None:
    """Even SQL that bypasses the repository cannot change or remove a funnel fact."""
    started = build_funnel_event()
    unit_of_work.funnel_events.append(started)
    with (
        pytest.raises(ProgrammingError, match="funnel_event is append-only"),
        database_connection.begin_nested(),
    ):
        database_connection.execute(text(modifying_statement), {"id": started.id})
    assert unit_of_work.funnel_events.list_for_sale(SALE_ID) == (started,)


class SimulatedUseCaseFailureError(Exception):
    """Stands for any error a use case meets after it wrote the sale and its funnel row."""


def start_sale_then_fail(session_factory: sessionmaker[Session], fixed_clock: FixedClock) -> None:
    """Writes the sale and its STARTED row in one unit of work, then fails before the commit."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.sales.add(build_sale())
        unit_of_work.funnel_events.append(build_funnel_event())
        raise SimulatedUseCaseFailureError


def test_unit_of_work_rolls_back_the_sale_and_its_funnel_event_together(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """A failure after both writes leaves neither the sale nor its STARTED row behind."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.merchants.add(build_merchant())
        unit_of_work.products.add(build_catalogue_product())
    with pytest.raises(SimulatedUseCaseFailureError):
        start_sale_then_fail(session_factory, fixed_clock)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as reading_unit_of_work:
        assert reading_unit_of_work.sales.find_by_id_for_update(SALE_ID) is None
        assert reading_unit_of_work.funnel_events.list_for_sale(SALE_ID) == ()
