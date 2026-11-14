"""SqlAlchemyUnitOfWork: one database transaction per use case, shared by every repository."""

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.core.clock import Clock
from emi_copilot.repositories.audit_event_repository import AuditEventRepository
from emi_copilot.repositories.payment_attempt_repository import PaymentAttemptRepository


# Pattern: Unit of Work. A payment attempt and its audit event commit together or not at all.
class SqlAlchemyUnitOfWork:
    """Opens a session and transaction on entry; commits on a clean exit, rolls back on any error.

    Use one instance per use case: `with unit_of_work: ...`. The repositories exist only inside
    the `with` block and all share its transaction. An instance is not re-entrant.
    """

    payment_attempts: PaymentAttemptRepository
    audit_events: AuditEventRepository
    _session: Session

    def __init__(self, session_factory: sessionmaker[Session], clock: Clock) -> None:
        """Keeps the session factory and the clock the repositories stamp timestamps with."""
        self._session_factory = session_factory
        self._clock = clock

    def __enter__(self) -> Self:
        """Starts a new session and transaction and builds the repositories on it."""
        session = self._session_factory()
        session.begin()
        self._session = session
        self.payment_attempts = PaymentAttemptRepository(session, self._clock)
        self.audit_events = AuditEventRepository(session, self._clock)
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Commits if the block finished normally, otherwise rolls back; always closes the session.

        The exception, if any, is never swallowed: it propagates after the rollback.
        """
        try:
            if exception_type is None:
                self._session.commit()
            else:
                self._session.rollback()
        finally:
            self._session.close()
