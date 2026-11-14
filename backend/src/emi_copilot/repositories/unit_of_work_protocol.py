"""What services and event subscribers need from a unit of work, so tests can use fakes.

SqlAlchemyUnitOfWork and its repositories satisfy these protocols structurally; services and
subscribers type against the protocols and never against SQLAlchemy.
"""

from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self

from emi_copilot.domain.payments import AuditEvent, PaymentAttempt


class PaymentAttemptStore(Protocol):
    """Adds, finds and updates payment attempts inside one transaction."""

    def add(self, payment_attempt: PaymentAttempt) -> None:
        """Inserts a new attempt; a duplicate id, order id or key raises a typed error."""
        ...

    def find_by_idempotency_key(self, idempotency_key: str) -> PaymentAttempt | None:
        """Returns the attempt stored under an Idempotency-Key, or None."""
        ...

    def find_by_order_id(self, order_id: str) -> PaymentAttempt | None:
        """Returns the attempt for one gateway order id, or None."""
        ...

    def update(self, payment_attempt: PaymentAttempt) -> PaymentAttempt:
        """Saves the mutable fields of a stored attempt and returns the stored attempt."""
        ...


class AuditEventStore(Protocol):
    """Appends audit events; there is deliberately no update or delete."""

    def append(self, audit_event: AuditEvent) -> None:
        """Inserts one audit event."""
        ...


class UnitOfWork(Protocol):
    """One transaction: commits on a clean exit of the `with` block, rolls back on any error."""

    @property
    def payment_attempts(self) -> PaymentAttemptStore:
        """Gives the payment attempt repository of this transaction."""
        ...

    @property
    def audit_events(self) -> AuditEventStore:
        """Gives the audit event repository of this transaction."""
        ...

    def __enter__(self) -> Self:
        """Starts the transaction and makes the repositories available."""
        ...

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Commits after a clean block, otherwise rolls back; never swallows the exception."""
        ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
"""Builds a fresh unit of work for each transaction a use case needs."""
