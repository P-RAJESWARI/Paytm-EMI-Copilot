"""Stores and loads customer sessions; a session is found by its token hash, never its token."""

from datetime import UTC

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.customer_sessions import (
    ComfortCheckStatus,
    CustomerLanguage,
    CustomerSession,
)
from emi_copilot.domain.errors import CustomerSessionNotFoundError
from emi_copilot.domain.money import Money
from emi_copilot.models import CustomerSessionModel


def _to_domain(session_model: CustomerSessionModel) -> CustomerSession:
    """Maps an ORM row back to a validated domain entity; every moment is returned in UTC."""
    return CustomerSession(
        id=session_model.id,
        sale_id=session_model.sale_id,
        token_hash=session_model.token_hash,
        created_at=session_model.created_at.astimezone(UTC),
        expires_at=session_model.expires_at.astimezone(UTC),
        monthly_budget=(
            None
            if session_model.monthly_budget_in_paise is None
            else Money.from_paise(session_model.monthly_budget_in_paise)
        ),
        comfort_check_status=ComfortCheckStatus(session_model.comfort_check_status),
        language=None
        if session_model.language is None
        else CustomerLanguage(session_model.language),
        revoked_at=(
            None if session_model.revoked_at is None else session_model.revoked_at.astimezone(UTC)
        ),
    )


def _copy_mutable_fields(
    customer_session: CustomerSession, session_model: CustomerSessionModel
) -> None:
    """Copies the fields a session may change after it starts onto its row."""
    session_model.monthly_budget_in_paise = (
        None
        if customer_session.monthly_budget is None
        else customer_session.monthly_budget.to_paise()
    )
    session_model.comfort_check_status = customer_session.comfort_check_status.value
    session_model.language = (
        None if customer_session.language is None else customer_session.language.value
    )
    session_model.revoked_at = customer_session.revoked_at


# Pattern: Repository. Keeps session queries out of the customer services.
class CustomerSessionRepository:
    """Adds, updates and finds customer sessions inside the unit of work's session."""

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for updated_at."""
        self._session = session
        self._clock = clock

    def add(self, customer_session: CustomerSession) -> None:
        """Inserts a new session now; created_at is the session's own start moment."""
        session_model = CustomerSessionModel(
            id=customer_session.id,
            sale_id=customer_session.sale_id,
            token_hash=customer_session.token_hash,
            expires_at=customer_session.expires_at,
            created_at=customer_session.created_at,
            updated_at=self._clock.now(),
        )
        _copy_mutable_fields(customer_session, session_model)
        self._session.add(session_model)
        self._session.flush()

    def update(self, customer_session: CustomerSession) -> CustomerSession:
        """Saves budget, comfort choice, language and revocation; returns the stored session.

        Identity, sale, token hash, start and expiry never change.
        """
        session_model = self._session.get(CustomerSessionModel, customer_session.id)
        if session_model is None:
            raise CustomerSessionNotFoundError("No customer session with this id is stored.")
        _copy_mutable_fields(customer_session, session_model)
        session_model.updated_at = self._clock.now()
        self._session.flush()
        return _to_domain(session_model)

    def find_by_token_hash(self, token_hash: str) -> CustomerSession | None:
        """Returns the session whose token hashes to this value, or None."""
        return self._find_one(
            select(CustomerSessionModel).where(CustomerSessionModel.token_hash == token_hash)
        )

    def find_by_id_for_update(self, customer_session_id: str) -> CustomerSession | None:
        """Returns the session with this id, locked until the transaction ends, or None."""
        return self._find_one(
            select(CustomerSessionModel)
            .where(CustomerSessionModel.id == customer_session_id)
            .with_for_update()
        )

    def list_unrevoked_for_sale_for_update(self, sale_id: str) -> tuple[CustomerSession, ...]:
        """Lists the sale's sessions not yet revoked, oldest first, rows locked.

        A new QR exchange revokes these (ADR 0022 decision 4); expired ones are included too.
        """
        statement = (
            select(CustomerSessionModel)
            .where(
                (CustomerSessionModel.sale_id == sale_id)
                & CustomerSessionModel.revoked_at.is_(None)
            )
            .order_by(CustomerSessionModel.created_at, CustomerSessionModel.id)
            .with_for_update()
        )
        return tuple(
            _to_domain(session_model) for session_model in self._session.scalars(statement)
        )

    def _find_one(self, statement: Select[CustomerSessionModel]) -> CustomerSession | None:
        """Loads at most one session for a query on a unique key."""
        session_model = self._session.scalars(statement).one_or_none()
        return None if session_model is None else _to_domain(session_model)
