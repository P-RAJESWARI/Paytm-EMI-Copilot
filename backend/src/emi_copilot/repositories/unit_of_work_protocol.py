"""What services and event subscribers need from a unit of work, so tests can use fakes.

SqlAlchemyUnitOfWork and its repositories satisfy these protocols structurally; services and
subscribers type against the protocols and never against SQLAlchemy.
"""

from collections.abc import Callable
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self

from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.funnel import FunnelEvent
from emi_copilot.domain.merchants import DevicePairing, Merchant
from emi_copilot.domain.payments import AuditEvent, PaymentAttempt
from emi_copilot.domain.sales import Sale, SaleStatus

AfterCommitCallback = Callable[[], None]
"""Work to run once a transaction has committed, such as telling live streams what changed."""


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

    def find_by_order_id_for_update(self, order_id: str) -> PaymentAttempt | None:
        """Returns the attempt for one order id, locked until the transaction ends, or None."""
        ...

    def update(self, payment_attempt: PaymentAttempt) -> PaymentAttempt:
        """Saves the mutable fields of a stored attempt and returns the stored attempt."""
        ...

    def find_latest_for_sale(self, sale_id: str) -> PaymentAttempt | None:
        """Returns the sale's most recently created attempt, or None when it has none."""
        ...


class AuditEventStore(Protocol):
    """Appends audit events; there is deliberately no update or delete."""

    def append(self, audit_event: AuditEvent) -> None:
        """Inserts one audit event."""
        ...


class MerchantStore(Protocol):
    """Adds, finds and updates merchants inside one transaction."""

    def add(self, merchant: Merchant) -> None:
        """Inserts a new merchant."""
        ...

    def find_by_id(self, merchant_id: str) -> Merchant | None:
        """Returns the merchant with this id, or None."""
        ...

    def find_by_shop_code_for_update(self, shop_code: str) -> Merchant | None:
        """Returns the merchant with this shop code, locked until the transaction ends, or None."""
        ...

    def lock_for_update(self, merchant_id: str) -> None:
        """Locks the merchant's row until the transaction ends, so its sales start one by one."""
        ...

    def update(self, merchant: Merchant) -> None:
        """Saves the mutable fields of a stored merchant."""
        ...


class DevicePairingStore(Protocol):
    """Adds device pairings and finds one by its access token hash inside one transaction."""

    def add(self, device_pairing: DevicePairing) -> None:
        """Inserts a new pairing."""
        ...

    def find_by_access_token_hash(self, access_token_hash: str) -> DevicePairing | None:
        """Returns the pairing whose token hashes to this value, or None."""
        ...


class ProductStore(Protocol):
    """Adds products and reads them for one merchant only, inside one transaction."""

    def add(self, product: CatalogueProduct) -> None:
        """Inserts a new product."""
        ...

    def list_for_merchant(
        self, merchant_id: str, name_search_text: str | None = None
    ) -> tuple[CatalogueProduct, ...]:
        """Lists the merchant's products dearest first, then by name; a search narrows them."""
        ...

    def find_by_id_for_merchant(self, merchant_id: str, product_id: str) -> CatalogueProduct | None:
        """Returns the product only if it belongs to the merchant, else None."""
        ...

    def find_by_gateway_product_id_for_merchant(
        self, merchant_id: str, gateway_product_id: str
    ) -> CatalogueProduct | None:
        """Returns the merchant's product with this gateway product id, or None."""
        ...


class SaleStore(Protocol):
    """Adds, updates, finds and lists sales inside one transaction."""

    def add(self, sale: Sale) -> None:
        """Inserts a new sale."""
        ...

    def update(self, sale: Sale) -> Sale:
        """Saves the mutable fields of a stored sale and returns the stored sale."""
        ...

    def find_by_id_for_merchant(self, merchant_id: str, sale_id: str) -> Sale | None:
        """Returns the sale only if it belongs to the merchant, else None."""
        ...

    def find_by_id_for_merchant_for_update(self, merchant_id: str, sale_id: str) -> Sale | None:
        """Returns the merchant's sale locked until the transaction ends, else None."""
        ...

    def find_by_id_for_update(self, sale_id: str) -> Sale | None:
        """Returns any sale by id, locked; for gateway reports and the customer flow only."""
        ...

    def find_by_idempotency_key_for_merchant(
        self, merchant_id: str, idempotency_key: str
    ) -> Sale | None:
        """Returns the merchant's sale started under this Idempotency-Key, or None."""
        ...

    def list_started_between_for_merchant(
        self,
        merchant_id: str,
        starts_at: datetime,
        ends_at: datetime,
        excluded_status: SaleStatus,
    ) -> tuple[Sale, ...]:
        """Lists the merchant's sales started in [starts_at, ends_at), newest first."""
        ...

    def list_choosing_started_by_for_merchant_for_update(
        self, merchant_id: str, started_at_or_before: datetime
    ) -> tuple[Sale, ...]:
        """Lists the merchant's CHOOSING sales started at or before a moment, rows locked."""
        ...

    def list_open_session_codes_for_merchant(self, merchant_id: str) -> frozenset[str]:
        """Gives the session codes on the merchant's open sales."""
        ...


class FunnelEventStore(Protocol):
    """Appends funnel events; there is deliberately no update or delete."""

    def append(self, funnel_event: FunnelEvent) -> None:
        """Inserts one funnel event; a second event for the same sale and stage fails."""
        ...

    def list_for_sale(self, sale_id: str) -> tuple[FunnelEvent, ...]:
        """Returns the stages one sale reached, oldest first."""
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

    @property
    def merchants(self) -> MerchantStore:
        """Gives the merchant repository of this transaction."""
        ...

    @property
    def device_pairings(self) -> DevicePairingStore:
        """Gives the device pairing repository of this transaction."""
        ...

    @property
    def products(self) -> ProductStore:
        """Gives the catalogue product repository of this transaction."""
        ...

    @property
    def sales(self) -> SaleStore:
        """Gives the sale repository of this transaction."""
        ...

    @property
    def funnel_events(self) -> FunnelEventStore:
        """Gives the funnel event repository of this transaction."""
        ...

    def call_after_commit(self, callback: AfterCommitCallback) -> None:
        """Queues work to run only after this transaction commits; a rollback drops it unrun."""
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
