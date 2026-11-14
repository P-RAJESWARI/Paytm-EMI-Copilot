"""In-memory unit of work and repositories that commit or roll back like the SQLAlchemy ones."""

from dataclasses import dataclass, field, replace
from types import TracebackType
from typing import Self

from emi_copilot.core.clock import Clock
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.errors import PaymentAttemptAlreadyExistsError, PaymentAttemptNotFoundError
from emi_copilot.domain.funnel import FunnelEvent
from emi_copilot.domain.merchants import DevicePairing, Merchant
from emi_copilot.domain.payments import AuditEvent, PaymentAttempt
from emi_copilot.domain.sales import Sale
from emi_copilot.repositories.after_commit_callbacks import AfterCommitCallbacks
from emi_copilot.repositories.unit_of_work_protocol import AfterCommitCallback
from tests.fakes.fake_merchant_repositories import (
    FakeDevicePairingRepository,
    FakeMerchantRepository,
    FakeProductRepository,
)
from tests.fakes.fake_sale_repositories import FakeFunnelEventRepository, FakeSaleRepository


@dataclass
class InMemoryDatabase:
    """The committed state every fake unit of work of one test shares, plus what happened to it."""

    payment_attempts_by_id: dict[str, PaymentAttempt] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)
    merchants_by_id: dict[str, Merchant] = field(default_factory=dict)
    device_pairings_by_id: dict[str, DevicePairing] = field(default_factory=dict)
    products_by_id: dict[str, CatalogueProduct] = field(default_factory=dict)
    sales_by_id: dict[str, Sale] = field(default_factory=dict)
    funnel_events: list[FunnelEvent] = field(default_factory=list)
    commit_count: int = 0
    rollback_count: int = 0

    def find_audit_events_for_subject(self, subject_id: str) -> list[AuditEvent]:
        """Lists the committed audit events about one subject, oldest first."""
        return [event for event in self.audit_events if event.subject_id == subject_id]


class FakePaymentAttemptRepository:
    """Holds attempts in a dict and enforces the three unique keys like the database does."""

    def __init__(self, payment_attempts_by_id: dict[str, PaymentAttempt], clock: Clock) -> None:
        """Works on the unit of work's private copy of the attempts."""
        self._payment_attempts_by_id = payment_attempts_by_id
        self._clock = clock

    def add(self, payment_attempt: PaymentAttempt) -> None:
        """Stores a new attempt; a duplicate id, order id or key raises the typed error."""
        for stored_attempt in self._payment_attempts_by_id.values():
            if (
                stored_attempt.id == payment_attempt.id
                or stored_attempt.order_id == payment_attempt.order_id
                or stored_attempt.idempotency_key == payment_attempt.idempotency_key
            ):
                raise PaymentAttemptAlreadyExistsError("A payment attempt already exists (fake).")
        self._payment_attempts_by_id[payment_attempt.id] = payment_attempt

    def find_by_idempotency_key(self, idempotency_key: str) -> PaymentAttempt | None:
        """Returns the attempt stored under the key, or None."""
        return next(
            (
                attempt
                for attempt in self._payment_attempts_by_id.values()
                if attempt.idempotency_key == idempotency_key
            ),
            None,
        )

    def find_by_order_id(self, order_id: str) -> PaymentAttempt | None:
        """Returns the attempt for the order id, or None."""
        return next(
            (
                attempt
                for attempt in self._payment_attempts_by_id.values()
                if attempt.order_id == order_id
            ),
            None,
        )

    def find_by_order_id_for_update(self, order_id: str) -> PaymentAttempt | None:
        """Returns the attempt for the order id; a single-threaded fake needs no lock."""
        return self.find_by_order_id(order_id)

    def find_latest_for_sale(self, sale_id: str) -> PaymentAttempt | None:
        """Returns the sale's newest attempt by creation time, then id, as the real query does."""
        sale_attempts = [
            attempt
            for attempt in self._payment_attempts_by_id.values()
            if attempt.sale_id == sale_id
        ]
        return max(
            sale_attempts, key=lambda attempt: (attempt.created_at, attempt.id), default=None
        )

    def update(self, payment_attempt: PaymentAttempt) -> PaymentAttempt:
        """Saves only the mutable fields and stamps updated_at, as the real repository does."""
        stored_attempt = self._payment_attempts_by_id.get(payment_attempt.id)
        if stored_attempt is None:
            raise PaymentAttemptNotFoundError("No such payment attempt (fake).")
        updated_attempt = replace(
            stored_attempt,
            status=payment_attempt.status,
            gateway_link_id=payment_attempt.gateway_link_id,
            payment_link_url=payment_attempt.payment_link_url,
            gateway_transaction_id=payment_attempt.gateway_transaction_id,
            failure_code=payment_attempt.failure_code,
            updated_at=self._clock.now(),
        )
        self._payment_attempts_by_id[payment_attempt.id] = updated_attempt
        return updated_attempt


class FakeAuditEventRepository:
    """Appends audit events to a list; like the real one it cannot update or delete."""

    def __init__(self, audit_events: list[AuditEvent]) -> None:
        """Works on the unit of work's private copy of the audit trail."""
        self._audit_events = audit_events

    def append(self, audit_event: AuditEvent) -> None:
        """Appends one audit event."""
        self._audit_events.append(audit_event)


class FakeUnitOfWork:
    """Copies the committed state on entry and publishes the copy only on a clean exit.

    Like the real one, it runs after-commit callbacks only once the copy is published.
    """

    payment_attempts: FakePaymentAttemptRepository
    audit_events: FakeAuditEventRepository
    merchants: FakeMerchantRepository
    device_pairings: FakeDevicePairingRepository
    products: FakeProductRepository
    sales: FakeSaleRepository
    funnel_events: FakeFunnelEventRepository

    def __init__(self, database: InMemoryDatabase, clock: Clock) -> None:
        """Keeps the shared in-memory database and the clock for updated_at."""
        self._database = database
        self._clock = clock
        self._working_attempts: dict[str, PaymentAttempt] = {}
        self._working_audit_events: list[AuditEvent] = []
        self._working_merchants: dict[str, Merchant] = {}
        self._working_device_pairings: dict[str, DevicePairing] = {}
        self._working_products: dict[str, CatalogueProduct] = {}
        self._working_sales: dict[str, Sale] = {}
        self._working_funnel_events: list[FunnelEvent] = []
        self._after_commit_callbacks = AfterCommitCallbacks()

    def __enter__(self) -> Self:
        """Starts a transaction on private copies of every committed collection."""
        self._working_attempts = dict(self._database.payment_attempts_by_id)
        self._working_audit_events = list(self._database.audit_events)
        self._working_merchants = dict(self._database.merchants_by_id)
        self._working_device_pairings = dict(self._database.device_pairings_by_id)
        self._working_products = dict(self._database.products_by_id)
        self._working_sales = dict(self._database.sales_by_id)
        self._working_funnel_events = list(self._database.funnel_events)
        self._after_commit_callbacks = AfterCommitCallbacks()
        self.payment_attempts = FakePaymentAttemptRepository(self._working_attempts, self._clock)
        self.audit_events = FakeAuditEventRepository(self._working_audit_events)
        self.merchants = FakeMerchantRepository(self._working_merchants)
        self.device_pairings = FakeDevicePairingRepository(self._working_device_pairings)
        self.products = FakeProductRepository(self._working_products)
        self.sales = FakeSaleRepository(self._working_sales)
        self.funnel_events = FakeFunnelEventRepository(self._working_funnel_events)
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
        """Commits the copies after a clean block, otherwise discards them; never swallows."""
        if exception_type is None:
            self._database.payment_attempts_by_id = self._working_attempts
            self._database.audit_events = self._working_audit_events
            self._database.merchants_by_id = self._working_merchants
            self._database.device_pairings_by_id = self._working_device_pairings
            self._database.products_by_id = self._working_products
            self._database.sales_by_id = self._working_sales
            self._database.funnel_events = self._working_funnel_events
            self._database.commit_count += 1
            self._after_commit_callbacks.run_all()
        else:
            self._database.rollback_count += 1
            self._after_commit_callbacks.discard_all()


class FakeUnitOfWorkFactory:
    """Builds a fresh FakeUnitOfWork on the shared database for every transaction."""

    def __init__(self, database: InMemoryDatabase, clock: Clock) -> None:
        """Keeps the database and clock every unit of work shares."""
        self.database = database
        self._clock = clock

    def __call__(self) -> FakeUnitOfWork:
        """Returns a new unit of work."""
        return FakeUnitOfWork(self.database, self._clock)
