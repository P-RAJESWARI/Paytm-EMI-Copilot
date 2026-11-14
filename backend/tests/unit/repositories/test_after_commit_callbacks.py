"""Tests for after-commit callbacks, on their own and inside the fake unit of work."""

import logging

import pytest

from emi_copilot.repositories.after_commit_callbacks import AfterCommitCallbacks
from tests.fakes.fake_unit_of_work import FakeUnitOfWorkFactory, InMemoryDatabase
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT

SECRET_LOOKING_MESSAGE = "Bearer synthetic-token-not-for-logs"  # noqa: S105  # pragma: allowlist secret


class SimulatedUseCaseFailureError(Exception):
    """Stands in for any error a service raises inside a unit of work."""


class SimulatedCallbackFailureError(Exception):
    """Stands in for a live stream that cannot take a message."""


def test_run_all_runs_queued_callbacks_in_order_once() -> None:
    """Callbacks run in the order they were queued, and a second run finds nothing left."""
    calls: list[str] = []
    callbacks = AfterCommitCallbacks()
    callbacks.add(lambda: calls.append("first"))
    callbacks.add(lambda: calls.append("second"))
    callbacks.run_all()
    callbacks.run_all()
    assert calls == ["first", "second"]


def test_discard_all_drops_queued_callbacks_unrun() -> None:
    """A rollback's callbacks never run."""
    calls: list[str] = []
    callbacks = AfterCommitCallbacks()
    callbacks.add(lambda: calls.append("dropped"))
    callbacks.discard_all()
    callbacks.run_all()
    assert calls == []


def _fail_with_secret_looking_message() -> None:
    """A callback whose error message must never reach the log."""
    raise SimulatedCallbackFailureError(SECRET_LOOKING_MESSAGE)


def test_run_all_logs_a_failing_callback_by_type_only_and_runs_the_rest(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failure is logged without its message or traceback and never stops the next callback."""
    calls: list[str] = []
    callbacks = AfterCommitCallbacks()
    callbacks.add(_fail_with_secret_looking_message)
    callbacks.add(lambda: calls.append("still runs"))
    with caplog.at_level(logging.ERROR):
        callbacks.run_all()
    assert calls == ["still runs"]
    (record,) = caplog.records
    assert record.getMessage() == "after-commit callback failed"
    assert record.__dict__["error_type"] == "SimulatedCallbackFailureError"
    assert record.exc_info is None
    assert SECRET_LOOKING_MESSAGE not in caplog.text


def _build_factory() -> FakeUnitOfWorkFactory:
    """A fake unit-of-work factory on an empty in-memory database."""
    return FakeUnitOfWorkFactory(InMemoryDatabase(), FixedClock(CREATED_AT))


def test_fake_unit_of_work_runs_callbacks_after_publishing_the_commit() -> None:
    """The callback sees the committed state, as it would with the real database."""
    factory = _build_factory()
    commit_counts_seen: list[int] = []
    with factory() as unit_of_work:
        unit_of_work.call_after_commit(
            lambda: commit_counts_seen.append(factory.database.commit_count)
        )
        assert commit_counts_seen == []
    assert commit_counts_seen == [1]


def test_fake_unit_of_work_never_runs_callbacks_after_a_rollback() -> None:
    """Work queued in a failed transaction is dropped with it."""
    factory = _build_factory()
    calls: list[str] = []

    def queue_callback_then_fail() -> None:
        """Queues a callback and fails before the end of the block."""
        with factory() as unit_of_work:
            unit_of_work.call_after_commit(lambda: calls.append("must not run"))
            raise SimulatedUseCaseFailureError

    with pytest.raises(SimulatedUseCaseFailureError):
        queue_callback_then_fail()
    assert calls == []
    assert factory.database.rollback_count == 1
