"""Appends and reads hash-chained consent records; there is deliberately no update or delete."""

from datetime import UTC
from typing import Final

from psycopg.errors import UniqueViolation
from sqlalchemy import Select, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.consent import (
    ConsentEvidence,
    ConsentIdempotency,
    ConsentPlanSnapshot,
    ConsentRecord,
    ConsentReference,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import ConsentAlreadyGivenError, ConsentRecordChainConflictError
from emi_copilot.models import ConsentRecordModel

# One fixed key for the whole chain: "CONSENT1" read as a big-endian 64-bit integer.
CONSENT_CHAIN_ADVISORY_LOCK_KEY: Final = int.from_bytes(b"CONSENT1", "big")
_ONE_CONSENT_PER_SALE_CONSTRAINT = "uq_consent_record_sale_id"


def _to_domain(record_model: ConsentRecordModel) -> ConsentRecord:
    """Maps an ORM row back to a validated record; a hash that no longer matches still loads.

    Loading never re-checks the hash, so verify_consent_record_chain can report tampering.
    """
    return ConsentRecord(
        evidence=ConsentEvidence(
            consent_id=record_model.id,
            sale_id=record_model.sale_id,
            customer_session_id=record_model.customer_session_id,
            consent_reference=ConsentReference(record_model.consent_reference),
            plan_snapshot=ConsentPlanSnapshot.from_dictionary(record_model.plan_snapshot),
            phone_last_two_digits=record_model.phone_last_two_digits,
            phone_hash=record_model.phone_hash,
            language=CustomerLanguage(record_model.language),
            cooling_off_wording_version=record_model.cooling_off_wording_version,
            consented_at=record_model.consented_at.astimezone(UTC),
        ),
        idempotency=ConsentIdempotency(
            record_model.idempotency_key, record_model.request_fingerprint
        ),
        chain_position=record_model.chain_position,
        previous_record_hash=record_model.previous_record_hash,
        record_hash=record_model.record_hash,
    )


def _to_model(consent_record: ConsentRecord) -> ConsentRecordModel:
    """Maps a record to a new row; money in the snapshot is integer paise."""
    evidence = consent_record.evidence
    return ConsentRecordModel(
        id=evidence.consent_id,
        chain_position=consent_record.chain_position,
        sale_id=evidence.sale_id,
        customer_session_id=evidence.customer_session_id,
        consent_reference=evidence.consent_reference.value,
        plan_snapshot=dict(evidence.plan_snapshot.to_dictionary()),
        phone_last_two_digits=evidence.phone_last_two_digits,
        phone_hash=evidence.phone_hash,
        language=evidence.language.value,
        cooling_off_wording_version=evidence.cooling_off_wording_version,
        consented_at=evidence.consented_at,
        previous_record_hash=consent_record.previous_record_hash,
        record_hash=consent_record.record_hash,
        idempotency_key=consent_record.idempotency.idempotency_key,
        request_fingerprint=consent_record.idempotency.request_fingerprint,
    )


# Pattern: Repository. The append-only consent chain; the missing update/delete is the point.
class ConsentRecordRepository:
    """Appends consent records and reads them back, inside the unit of work's session.

    A database trigger also rejects UPDATE, DELETE and TRUNCATE on consent_record, and unique
    constraints allow one consent per sale and stop the chain from forking.
    """

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for each row's created_at."""
        self._session = session
        self._clock = clock

    def find_latest_for_update(self) -> ConsentRecord | None:
        """Takes the chain lock until the transaction ends, then gives the chain head, or None.

        A transaction-scoped advisory lock, not a row lock, because a waiting row lock on
        "ORDER BY ... LIMIT 1" would wake up holding the old head instead of the new one. Every
        append calls this first, so appends follow one another.
        """
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": CONSENT_CHAIN_ADVISORY_LOCK_KEY},
        )
        return self._find_one(
            select(ConsentRecordModel).order_by(ConsentRecordModel.chain_position.desc()).limit(1)
        )

    def append(self, consent_record: ConsentRecord) -> None:
        """Inserts one record now; a second consent for the sale or a fork raises a typed error."""
        record_model = _to_model(consent_record)
        record_model.created_at = self._clock.now()
        try:
            with self._session.begin_nested():
                self._session.add(record_model)
        except IntegrityError as integrity_error:
            if not isinstance(integrity_error.orig, UniqueViolation):
                raise
            if integrity_error.orig.diag.constraint_name == _ONE_CONSENT_PER_SALE_CONSTRAINT:
                raise ConsentAlreadyGivenError(
                    "This sale already has a consent record."
                ) from integrity_error
            raise ConsentRecordChainConflictError(
                "Another consent record took this place in the chain."
            ) from integrity_error

    def list_in_order(self) -> tuple[ConsentRecord, ...]:
        """Returns the whole chain from the first record, for verify_consent_record_chain."""
        statement = select(ConsentRecordModel).order_by(ConsentRecordModel.chain_position)
        return tuple(_to_domain(record_model) for record_model in self._session.scalars(statement))

    def find_for_sale(self, sale_id: str) -> ConsentRecord | None:
        """Returns the sale's consent record, or None before the customer agreed."""
        return self._find_one(
            select(ConsentRecordModel).where(ConsentRecordModel.sale_id == sale_id)
        )

    def _find_one(self, statement: Select[ConsentRecordModel]) -> ConsentRecord | None:
        """Loads at most one record for a query on a unique key or a LIMIT 1."""
        record_model = self._session.scalars(statement).one_or_none()
        return None if record_model is None else _to_domain(record_model)
