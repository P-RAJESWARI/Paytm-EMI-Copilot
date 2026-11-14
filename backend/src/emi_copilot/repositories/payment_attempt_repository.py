"""Stores and loads payment attempts, mapping ORM rows to domain entities at this boundary."""

from datetime import UTC

from psycopg.errors import UniqueViolation
from sqlalchemy import ColumnElement, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import PaymentAttemptAlreadyExistsError, PaymentAttemptNotFoundError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    OfferSnapshot,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentLinkFailureCode,
)
from emi_copilot.models import PaymentAttemptModel


def _failure_code_value(failure_code: PaymentLinkFailureCode | None) -> str | None:
    """Gives the stored word of a failure code, or None when the attempt has not failed."""
    return None if failure_code is None else failure_code.value


def _to_model(payment_attempt: PaymentAttempt) -> PaymentAttemptModel:
    """Maps a domain payment attempt to a new ORM row, with money as integer paise."""
    return PaymentAttemptModel(
        id=payment_attempt.id,
        order_id=payment_attempt.order_id,
        idempotency_key=payment_attempt.idempotency_key,
        request_fingerprint=payment_attempt.request_fingerprint,
        amount_in_paise=payment_attempt.amount.to_paise(),
        status=payment_attempt.status.value,
        offer_snapshot=dict(payment_attempt.offer_snapshot.to_dictionary()),
        gateway_mode=payment_attempt.gateway_mode,
        gateway_link_id=payment_attempt.gateway_link_id,
        payment_link_url=payment_attempt.payment_link_url,
        gateway_transaction_id=payment_attempt.gateway_transaction_id,
        created_at=payment_attempt.created_at,
        updated_at=payment_attempt.updated_at,
        failure_code=_failure_code_value(payment_attempt.failure_code),
    )


def _to_domain(payment_attempt_model: PaymentAttemptModel) -> PaymentAttempt:
    """Maps an ORM row back to a validated domain entity; timestamps are returned in UTC."""
    return PaymentAttempt(
        id=payment_attempt_model.id,
        order_id=payment_attempt_model.order_id,
        idempotency_key=payment_attempt_model.idempotency_key,
        request_fingerprint=payment_attempt_model.request_fingerprint,
        amount=Money.from_paise(payment_attempt_model.amount_in_paise),
        status=PaymentAttemptStatus(payment_attempt_model.status),
        offer_snapshot=OfferSnapshot.from_dictionary(payment_attempt_model.offer_snapshot),
        gateway_mode=payment_attempt_model.gateway_mode,
        gateway_link_id=payment_attempt_model.gateway_link_id,
        payment_link_url=payment_attempt_model.payment_link_url,
        gateway_transaction_id=payment_attempt_model.gateway_transaction_id,
        created_at=payment_attempt_model.created_at.astimezone(UTC),
        updated_at=payment_attempt_model.updated_at.astimezone(UTC),
        failure_code=(
            None
            if payment_attempt_model.failure_code is None
            else PaymentLinkFailureCode(payment_attempt_model.failure_code)
        ),
    )


# Pattern: Repository. Keeps every payment_attempt query out of services; no business rules here.
class PaymentAttemptRepository:
    """Adds, finds and updates payment attempts inside the unit of work's session."""

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for updated_at."""
        self._session = session
        self._clock = clock

    def add(self, payment_attempt: PaymentAttempt) -> None:
        """Inserts a new attempt now; a duplicate id, order id or key raises a typed error.

        The insert runs in a savepoint, so after a duplicate the session is still usable and the
        caller can read the attempt that won the race.
        """
        try:
            with self._session.begin_nested():
                self._session.add(_to_model(payment_attempt))
        except IntegrityError as integrity_error:
            if isinstance(integrity_error.orig, UniqueViolation):
                constraint_name = integrity_error.orig.diag.constraint_name
                raise PaymentAttemptAlreadyExistsError(
                    f"A payment attempt already exists ({constraint_name})."
                ) from integrity_error
            raise

    def find_by_idempotency_key(self, idempotency_key: str) -> PaymentAttempt | None:
        """Returns the attempt stored under an Idempotency-Key, or None if there is none."""
        return self._find_one_where(PaymentAttemptModel.idempotency_key == idempotency_key)

    def find_by_order_id(self, order_id: str) -> PaymentAttempt | None:
        """Returns the attempt for one gateway order id, or None if there is none."""
        return self._find_one_where(PaymentAttemptModel.order_id == order_id)

    def update(self, payment_attempt: PaymentAttempt) -> PaymentAttempt:
        """Saves the mutable fields (status, gateway references, failure code); stamps updated_at.

        Identity, keys, fingerprint, amount, snapshot and gateway mode never change after
        insertion, so their values on the given attempt are ignored. Returns the stored attempt.
        """
        payment_attempt_model = self._session.get(PaymentAttemptModel, payment_attempt.id)
        if payment_attempt_model is None:
            raise PaymentAttemptNotFoundError(
                f"No payment attempt with id {payment_attempt.id} is stored."
            )
        payment_attempt_model.status = payment_attempt.status.value
        payment_attempt_model.gateway_link_id = payment_attempt.gateway_link_id
        payment_attempt_model.payment_link_url = payment_attempt.payment_link_url
        payment_attempt_model.gateway_transaction_id = payment_attempt.gateway_transaction_id
        payment_attempt_model.failure_code = _failure_code_value(payment_attempt.failure_code)
        payment_attempt_model.updated_at = self._clock.now()
        self._session.flush()
        return _to_domain(payment_attempt_model)

    def find_by_order_id_for_update(self, order_id: str) -> PaymentAttempt | None:
        """Returns the attempt for one order id, locking its row until the transaction ends.

        Two reports about one order (a webhook and a status check) then apply one after the
        other, so a status change is recorded once.
        """
        return self._find_one_where(
            PaymentAttemptModel.order_id == order_id, is_locked_for_update=True
        )

    def _find_one_where(
        self, condition: ColumnElement[bool], *, is_locked_for_update: bool = False
    ) -> PaymentAttempt | None:
        """Loads at most one attempt matching a condition on a unique column, maybe locking it."""
        statement = select(PaymentAttemptModel).where(condition)
        if is_locked_for_update:
            statement = statement.with_for_update()
        payment_attempt_model = self._session.scalars(statement).one_or_none()
        return None if payment_attempt_model is None else _to_domain(payment_attempt_model)
