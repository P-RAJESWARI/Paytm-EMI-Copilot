"""Integration tests for SqlAlchemyUnitOfWork: both rows commit together or neither does."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.payments import PaymentAttempt
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.fixed_clock import FixedClock
from tests.payment_builders import build_audit_event, build_payment_attempt

pytestmark = pytest.mark.integration


class SimulatedUseCaseFailureError(Exception):
    """Stands in for any error a service raises after writing inside a unit of work."""


def _stored_attempt_and_events(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock, attempt: PaymentAttempt
) -> tuple[PaymentAttempt | None, int]:
    """Reads, in a fresh unit of work, the stored attempt and how many audit rows it has."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        stored_attempt = unit_of_work.payment_attempts.find_by_idempotency_key(
            attempt.idempotency_key
        )
        audit_events = unit_of_work.audit_events.list_for_subject("payment_attempt", attempt.id)
    return stored_attempt, len(audit_events)


def test_unit_of_work_commits_attempt_and_audit_event_together(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """A clean exit commits the payment attempt and its audit row in one transaction."""
    payment_attempt = build_payment_attempt()
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.payment_attempts.add(payment_attempt)
        unit_of_work.audit_events.append(build_audit_event(subject_id=payment_attempt.id))
    assert _stored_attempt_and_events(session_factory, fixed_clock, payment_attempt) == (
        payment_attempt,
        1,
    )


def _write_attempt_and_audit_event_then_fail(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock, attempt: PaymentAttempt
) -> None:
    """Writes an attempt and its audit row in one unit of work, then fails before the end."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.payment_attempts.add(attempt)
        unit_of_work.audit_events.append(build_audit_event(subject_id=attempt.id))
        raise SimulatedUseCaseFailureError


def test_unit_of_work_rolls_back_both_rows_when_the_block_raises(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """An error after both writes undoes both, and the error still reaches the caller."""
    payment_attempt = build_payment_attempt()
    with pytest.raises(SimulatedUseCaseFailureError):
        _write_attempt_and_audit_event_then_fail(session_factory, fixed_clock, payment_attempt)
    assert _stored_attempt_and_events(session_factory, fixed_clock, payment_attempt) == (None, 0)


def test_unit_of_work_shares_one_session_between_its_repositories(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """A row written through one repository is visible to a read in the same unit of work."""
    payment_attempt = build_payment_attempt()
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.payment_attempts.add(payment_attempt)
        assert unit_of_work.payment_attempts.find_by_order_id(payment_attempt.order_id) == (
            payment_attempt
        )
