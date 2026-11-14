"""In-memory sale and funnel event repositories that behave like the SQLAlchemy ones."""

from datetime import datetime

from emi_copilot.domain.errors import InvalidSaleDataError, SaleNotFoundError
from emi_copilot.domain.funnel import FunnelEvent
from emi_copilot.domain.sales import OPEN_SALE_STATUSES, Sale, SaleStatus


class FakeSaleRepository:
    """Holds sales in a dict; enforces the unique keys and open session codes like the database."""

    def __init__(self, sales_by_id: dict[str, Sale]) -> None:
        """Works on the unit of work's private copy of the sales."""
        self._sales_by_id = sales_by_id

    def add(self, sale: Sale) -> None:
        """Stores a new sale; a duplicate id, key or open session code fails as in the database."""
        for stored in self._sales_by_id.values():
            is_same_key = (
                sale.idempotency is not None
                and stored.idempotency is not None
                and stored.merchant_id == sale.merchant_id
                and stored.idempotency.idempotency_key == sale.idempotency.idempotency_key
            )
            is_same_open_code = (
                stored.merchant_id == sale.merchant_id
                and stored.session_code == sale.session_code
                and stored.status in OPEN_SALE_STATUSES
            )
            if stored.id == sale.id or is_same_key or is_same_open_code:
                raise InvalidSaleDataError("A sale with this id, key or open code exists (fake).")
        self._sales_by_id[sale.id] = sale

    def update(self, sale: Sale) -> Sale:
        """Replaces a stored sale; an unknown one fails as the real repository does."""
        if sale.id not in self._sales_by_id:
            raise SaleNotFoundError("No such sale (fake).")
        self._sales_by_id[sale.id] = sale
        return sale

    def find_by_id_for_merchant(self, merchant_id: str, sale_id: str) -> Sale | None:
        """Returns the sale only if it belongs to the merchant."""
        sale = self._sales_by_id.get(sale_id)
        return sale if sale is not None and sale.merchant_id == merchant_id else None

    def find_by_id_for_merchant_for_update(self, merchant_id: str, sale_id: str) -> Sale | None:
        """Returns the merchant's sale; a single-threaded fake needs no lock."""
        return self.find_by_id_for_merchant(merchant_id, sale_id)

    def find_by_id_for_update(self, sale_id: str) -> Sale | None:
        """Returns any sale by id."""
        return self._sales_by_id.get(sale_id)

    def find_by_idempotency_key_for_merchant(
        self, merchant_id: str, idempotency_key: str
    ) -> Sale | None:
        """Returns the merchant's sale started under the key, or None."""
        return next(
            (
                sale
                for sale in self._sales_by_id.values()
                if sale.merchant_id == merchant_id
                and sale.idempotency is not None
                and sale.idempotency.idempotency_key == idempotency_key
            ),
            None,
        )

    def list_started_between_for_merchant(
        self,
        merchant_id: str,
        starts_at: datetime,
        ends_at: datetime,
        excluded_status: SaleStatus,
    ) -> tuple[Sale, ...]:
        """Lists the merchant's sales started in [starts_at, ends_at), newest first."""
        matching_sales = [
            sale
            for sale in self._sales_by_id.values()
            if sale.merchant_id == merchant_id
            and starts_at <= sale.started_at < ends_at
            and sale.status is not excluded_status
        ]
        return tuple(
            sorted(matching_sales, key=lambda sale: (sale.started_at, sale.id), reverse=True)
        )

    def list_choosing_started_by_for_merchant_for_update(
        self, merchant_id: str, started_at_or_before: datetime
    ) -> tuple[Sale, ...]:
        """Lists the merchant's CHOOSING sales started at or before the moment, oldest first."""
        matching_sales = [
            sale
            for sale in self._sales_by_id.values()
            if sale.merchant_id == merchant_id
            and sale.status is SaleStatus.CHOOSING
            and sale.started_at <= started_at_or_before
        ]
        return tuple(sorted(matching_sales, key=lambda sale: (sale.started_at, sale.id)))

    def list_open_session_codes_for_merchant(self, merchant_id: str) -> frozenset[str]:
        """Gives the session codes on the merchant's open sales."""
        return frozenset(
            sale.session_code.value
            for sale in self._sales_by_id.values()
            if sale.merchant_id == merchant_id and sale.status in OPEN_SALE_STATUSES
        )


class FakeFunnelEventRepository:
    """Appends funnel events to a list; one event per sale and stage, never updated or deleted."""

    def __init__(self, funnel_events: list[FunnelEvent]) -> None:
        """Works on the unit of work's private copy of the funnel."""
        self._funnel_events = funnel_events

    def append(self, funnel_event: FunnelEvent) -> None:
        """Appends one event; a repeat of a sale's stage fails as the unique constraint would."""
        if any(
            stored.sale_id == funnel_event.sale_id and stored.stage is funnel_event.stage
            for stored in self._funnel_events
        ):
            raise InvalidSaleDataError("This sale already reached this stage (fake).")
        self._funnel_events.append(funnel_event)

    def list_for_sale(self, sale_id: str) -> tuple[FunnelEvent, ...]:
        """Returns the sale's events, oldest first."""
        return tuple(
            sorted(
                (event for event in self._funnel_events if event.sale_id == sale_id),
                key=lambda event: (event.occurred_at, event.id),
            )
        )
