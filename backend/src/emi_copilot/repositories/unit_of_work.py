"""SqlAlchemyUnitOfWork: one database transaction per use case, shared by every repository."""

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.core.clock import Clock
from emi_copilot.repositories.after_commit_callbacks import AfterCommitCallbacks
from emi_copilot.repositories.audit_event_repository import AuditEventRepository
from emi_copilot.repositories.device_pairing_repository import DevicePairingRepository
from emi_copilot.repositories.funnel_event_repository import FunnelEventRepository
from emi_copilot.repositories.merchant_repository import MerchantRepository
from emi_copilot.repositories.payment_attempt_repository import PaymentAttemptRepository
from emi_copilot.repositories.product_repository import ProductRepository
from emi_copilot.repositories.sale_repository import SaleRepository
from emi_copilot.repositories.unit_of_work_protocol import AfterCommitCallback


# Pattern: Unit of Work. A business write, its audit event and its funnel event commit together
# or not at all.
class SqlAlchemyUnitOfWork:
    """Opens a session and transaction on entry; commits on a clean exit, rolls back on any error.

    Use one instance per use case: `with unit_of_work: ...`. The repositories exist only inside
    the `with` block and all share its transaction. An instance is not re-entrant. Callbacks
    queued with call_after_commit run after a successful commit, never after a rollback.
    """

    payment_attempts: PaymentAttemptRepository
    audit_events: AuditEventRepository
    merchants: MerchantRepository
    device_pairings: DevicePairingRepository
    products: ProductRepository
    sales: SaleRepository
    funnel_events: FunnelEventRepository
    _session: Session

    def __init__(self, session_factory: sessionmaker[Session], clock: Clock) -> None:
        """Keeps the session factory and the clock the repositories stamp timestamps with."""
        self._session_factory = session_factory
        self._clock = clock
        self._after_commit_callbacks = AfterCommitCallbacks()

    def __enter__(self) -> Self:
        """Starts a new session and transaction and builds the repositories on it."""
        session = self._session_factory()
        session.begin()
        self._session = session
        self._after_commit_callbacks = AfterCommitCallbacks()
        self.payment_attempts = PaymentAttemptRepository(session, self._clock)
        self.audit_events = AuditEventRepository(session, self._clock)
        self.merchants = MerchantRepository(session, self._clock)
        self.device_pairings = DevicePairingRepository(session, self._clock)
        self.products = ProductRepository(session, self._clock)
        self.sales = SaleRepository(session, self._clock)
        self.funnel_events = FunnelEventRepository(session, self._clock)
        return self

    def call_after_commit(self, callback: AfterCommitCallback) -> None:
        """Queues work to run only after this transaction commits; a rollback drops it unrun."""
        self._after_commit_callbacks.add(callback)

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Commits if the block finished normally, otherwise rolls back; always closes the session.

        The exception, if any, is never swallowed: it propagates after the rollback. A failed
        commit raises too, and its queued callbacks are dropped like a rollback's.
        """
        has_committed = False
        try:
            if exception_type is None:
                self._session.commit()
                has_committed = True
            else:
                self._session.rollback()
        finally:
            self._session.close()
            if not has_committed:
                self._after_commit_callbacks.discard_all()
        self._after_commit_callbacks.run_all()
