"""Stores and loads sales; merchant-facing reads are scoped to one merchant."""

from datetime import UTC, datetime

from sqlalchemy import ColumnElement, Select, exists, select
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import SaleNotFoundError
from emi_copilot.domain.money import Money
from emi_copilot.domain.sales import (
    OPEN_SALE_STATUSES,
    ChosenPlan,
    CustomerQrTokenState,
    Sale,
    SaleIdempotency,
    SaleStatus,
    SessionCode,
)
from emi_copilot.models import SaleModel


def _in_utc(moment: datetime | None) -> datetime | None:
    """Gives a stored moment in UTC, keeping None as None."""
    return None if moment is None else moment.astimezone(UTC)


def _to_idempotency(
    idempotency_key: str | None, request_fingerprint: str | None
) -> SaleIdempotency | None:
    """Gives the stored key and fingerprint, or None for a sale started without a key."""
    if idempotency_key is None or request_fingerprint is None:
        return None
    return SaleIdempotency(idempotency_key, request_fingerprint)


def _to_domain(sale_model: SaleModel) -> Sale:
    """Maps an ORM row back to a validated domain entity; every moment is returned in UTC."""
    return Sale(
        id=sale_model.id,
        merchant_id=sale_model.merchant_id,
        product_id=sale_model.product_id,
        price=Money.from_paise(sale_model.price_in_paise),
        session_code=SessionCode(sale_model.session_code),
        status=SaleStatus(sale_model.status),
        chosen_plan=(
            None
            if sale_model.chosen_plan_snapshot is None
            else ChosenPlan.from_dictionary(sale_model.chosen_plan_snapshot)
        ),
        qr_token=CustomerQrTokenState(
            nonce_hash=sale_model.qr_token_nonce_hash,
            expires_at=sale_model.qr_token_expires_at.astimezone(UTC),
            exchanged_at=_in_utc(sale_model.qr_token_exchanged_at),
        ),
        started_at=sale_model.started_at.astimezone(UTC),
        status_changed_at=sale_model.status_changed_at.astimezone(UTC),
        idempotency=_to_idempotency(sale_model.idempotency_key, sale_model.request_fingerprint),
    )


def _copy_mutable_fields(sale: Sale, sale_model: SaleModel) -> None:
    """Copies the fields a sale may change after it starts onto its row."""
    sale_model.status = sale.status.value
    sale_model.status_changed_at = sale.status_changed_at
    sale_model.chosen_plan_snapshot = (
        None if sale.chosen_plan is None else dict(sale.chosen_plan.to_dictionary())
    )
    sale_model.qr_token_nonce_hash = sale.qr_token.nonce_hash
    sale_model.qr_token_expires_at = sale.qr_token.expires_at
    sale_model.qr_token_exchanged_at = sale.qr_token.exchanged_at


# Pattern: Repository. Merchant-facing queries all take a merchant id, so one shop never reads
# another's sales; the unscoped lookup exists only for gateway reports and the customer flow.
class SaleRepository:
    """Adds, updates, finds and lists sales inside the unit of work's session."""

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for created_at and updated_at."""
        self._session = session
        self._clock = clock

    def add(self, sale: Sale) -> None:
        """Inserts a new sale now, with its price as integer paise."""
        now = self._clock.now()
        sale_model = SaleModel(
            id=sale.id,
            merchant_id=sale.merchant_id,
            product_id=sale.product_id,
            price_in_paise=sale.price.to_paise(),
            session_code=sale.session_code.value,
            started_at=sale.started_at,
            idempotency_key=None if sale.idempotency is None else sale.idempotency.idempotency_key,
            request_fingerprint=(
                None if sale.idempotency is None else sale.idempotency.request_fingerprint
            ),
            created_at=now,
            updated_at=now,
        )
        _copy_mutable_fields(sale, sale_model)
        self._session.add(sale_model)
        self._session.flush()

    def update(self, sale: Sale) -> Sale:
        """Saves status, plan and QR token fields and stamps updated_at; returns the stored sale.

        Identity, merchant, product, price, code, start and idempotency never change.
        """
        sale_model = self._session.get(SaleModel, sale.id)
        if sale_model is None:
            raise SaleNotFoundError(f"No sale with id {sale.id} is stored.")
        _copy_mutable_fields(sale, sale_model)
        sale_model.updated_at = self._clock.now()
        self._session.flush()
        return _to_domain(sale_model)

    def find_by_id_for_merchant(self, merchant_id: str, sale_id: str) -> Sale | None:
        """Returns the sale only if it belongs to the merchant; another shop's gives None."""
        return self._find_one(self._select_for_merchant(merchant_id, SaleModel.id == sale_id))

    def find_by_id_for_merchant_for_update(self, merchant_id: str, sale_id: str) -> Sale | None:
        """Like find_by_id_for_merchant, but locks the row until the transaction ends."""
        return self._find_one(
            self._select_for_merchant(merchant_id, SaleModel.id == sale_id).with_for_update()
        )

    def find_by_id_for_update(self, sale_id: str) -> Sale | None:
        """Returns any sale by id, locked; for gateway reports and the customer flow only."""
        return self._find_one(select(SaleModel).where(SaleModel.id == sale_id).with_for_update())

    def find_by_idempotency_key_for_merchant(
        self, merchant_id: str, idempotency_key: str
    ) -> Sale | None:
        """Returns the merchant's sale started under this Idempotency-Key, or None."""
        return self._find_one(
            self._select_for_merchant(merchant_id, SaleModel.idempotency_key == idempotency_key)
        )

    def list_started_between_for_merchant(
        self,
        merchant_id: str,
        starts_at: datetime,
        ends_at: datetime,
        excluded_status: SaleStatus,
    ) -> tuple[Sale, ...]:
        """Lists the merchant's sales with starts_at <= started_at < ends_at, newest first.

        Sales in excluded_status are left out; ties on the start moment are broken by id.
        """
        statement = self._select_for_merchant(
            merchant_id,
            (SaleModel.started_at >= starts_at)
            & (SaleModel.started_at < ends_at)
            & (SaleModel.status != excluded_status.value),
        ).order_by(SaleModel.started_at.desc(), SaleModel.id.desc())
        return tuple(_to_domain(sale_model) for sale_model in self._session.scalars(statement))

    def list_choosing_started_by_for_merchant_for_update(
        self, merchant_id: str, started_at_or_before: datetime
    ) -> tuple[Sale, ...]:
        """Lists the merchant's CHOOSING sales started at or before a moment, rows locked."""
        statement = (
            self._select_for_merchant(
                merchant_id,
                (SaleModel.status == SaleStatus.CHOOSING.value)
                & (SaleModel.started_at <= started_at_or_before),
            )
            .order_by(SaleModel.started_at, SaleModel.id)
            .with_for_update()
        )
        return tuple(_to_domain(sale_model) for sale_model in self._session.scalars(statement))

    def has_any_for_merchant(self, merchant_id: str) -> bool:
        """Tells whether the merchant has any sale at all, in any status."""
        return bool(
            self._session.scalar(select(exists().where(SaleModel.merchant_id == merchant_id)))
        )

    def list_open_session_codes_for_merchant(self, merchant_id: str) -> frozenset[str]:
        """Gives the session codes on the merchant's open sales, which a new sale must avoid."""
        statement = select(SaleModel.session_code).where(
            (SaleModel.merchant_id == merchant_id)
            & SaleModel.status.in_([status.value for status in OPEN_SALE_STATUSES])
        )
        return frozenset(self._session.scalars(statement))

    def _select_for_merchant(
        self, merchant_id: str, condition: ColumnElement[bool]
    ) -> Select[SaleModel]:
        """Starts a query over one merchant's sales that also match a condition."""
        return select(SaleModel).where((SaleModel.merchant_id == merchant_id) & condition)

    def _find_one(self, statement: Select[SaleModel]) -> Sale | None:
        """Loads at most one sale for a query on a unique key."""
        sale_model = self._session.scalars(statement).one_or_none()
        return None if sale_model is None else _to_domain(sale_model)
