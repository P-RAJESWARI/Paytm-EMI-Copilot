"""Integration tests for the append-only, hash-chained ConsentRecordRepository and its guards."""

from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.consent import (
    GENESIS_PREVIOUS_RECORD_HASH,
    ConsentRecord,
    verify_consent_record_chain,
)
from emi_copilot.domain.errors import ConsentAlreadyGivenError, ConsentRecordChainConflictError
from emi_copilot.repositories.consent_record_repository import (
    CONSENT_CHAIN_ADVISORY_LOCK_KEY,
    ConsentRecordRepository,
)
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.consent_builders import (
    CONSENTED_AT,
    build_consent_evidence,
    build_consent_idempotency,
    build_first_consent_record,
)
from tests.fixed_clock import FixedClock
from tests.integration.repositories.customer_flow_storage import (
    OTHER_SALE_ID,
    store_sales_and_session,
)
from tests.sale_builders import SALE_ID

pytestmark = pytest.mark.integration

SECOND_CONSENT_ID = "01JCCONSENT000000000000002"


def build_second_record(first_record: ConsentRecord, **evidence_overrides: object) -> ConsentRecord:
    """A consent on the other sale a minute later, appended after first_record."""
    evidence_fields: dict[str, object] = {
        "consent_id": SECOND_CONSENT_ID,
        "sale_id": OTHER_SALE_ID,
        "consented_at": CONSENTED_AT + timedelta(minutes=1),
    }
    evidence_fields.update(evidence_overrides)
    return ConsentRecord.append_after(
        first_record,
        build_consent_evidence(**evidence_fields),
        build_consent_idempotency("consent-key-0002"),
    )


@pytest.fixture
def unit_of_work(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> Iterator[SqlAlchemyUnitOfWork]:
    """Stores the sample sales and session, then opens one unit of work for the test."""
    store_sales_and_session(session_factory, fixed_clock)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as opened_unit_of_work:
        yield opened_unit_of_work


def test_consent_record_repository_public_api_is_append_and_read_only() -> None:
    """No update or delete path exists for consent evidence (security section 9)."""
    public_names = {name for name in dir(ConsentRecordRepository) if not name.startswith("_")}
    assert public_names == {"append", "find_for_sale", "find_latest_for_update", "list_in_order"}


def test_appended_records_read_back_unchanged_in_chain_order_and_verify(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """The snapshot round-trips as paise; the head is the last record; the chain is intact."""
    assert unit_of_work.consent_records.find_latest_for_update() is None
    first_record = build_first_consent_record()
    unit_of_work.consent_records.append(first_record)
    assert unit_of_work.consent_records.find_latest_for_update() == first_record
    second_record = build_second_record(first_record)
    unit_of_work.consent_records.append(second_record)
    stored_chain = unit_of_work.consent_records.list_in_order()
    assert stored_chain == (first_record, second_record)
    assert verify_consent_record_chain(stored_chain).is_intact
    assert unit_of_work.consent_records.find_latest_for_update() == second_record
    assert unit_of_work.consent_records.find_for_sale(SALE_ID) == first_record
    assert unit_of_work.consent_records.find_for_sale("01JCSALE000000000000000099") is None


def test_find_latest_for_update_holds_the_chain_lock_until_the_transaction_ends(
    unit_of_work: SqlAlchemyUnitOfWork, database_connection: Connection
) -> None:
    """Appends follow one another because each first takes the one chain advisory lock."""
    unit_of_work.consent_records.find_latest_for_update()
    held_lock_count = database_connection.execute(
        text(
            "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted"
            " AND pid = pg_backend_pid()"
            " AND ((classid::bigint << 32) | objid::bigint) = :lock_key"
        ),
        {"lock_key": CONSENT_CHAIN_ADVISORY_LOCK_KEY},
    ).scalar_one()
    assert held_lock_count == 1


def test_a_second_consent_for_the_same_sale_is_refused(unit_of_work: SqlAlchemyUnitOfWork) -> None:
    """One sale has one consent; the session stays usable after the refusal."""
    first_record = build_first_consent_record()
    unit_of_work.consent_records.append(first_record)
    with pytest.raises(ConsentAlreadyGivenError):
        unit_of_work.consent_records.append(build_second_record(first_record, sale_id=SALE_ID))
    assert unit_of_work.consent_records.list_in_order() == (first_record,)


def test_a_forked_chain_is_refused(unit_of_work: SqlAlchemyUnitOfWork) -> None:
    """Two records claiming the same previous record (a lost race) cannot both be stored."""
    first_record = build_first_consent_record()
    unit_of_work.consent_records.append(first_record)
    unit_of_work.consent_records.append(build_second_record(first_record))
    fork = build_second_record(
        first_record, consent_id="01JCCONSENT000000000000003", sale_id="01JCSALE000000000000000003"
    )
    with pytest.raises(ConsentRecordChainConflictError):
        unit_of_work.consent_records.append(fork)


def test_two_records_racing_to_be_first_cannot_both_be_stored(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """The genesis link is a fixed value, so the unique previous hash stops a second first."""
    unit_of_work.consent_records.append(build_first_consent_record())
    second_first = ConsentRecord.append_after(
        None,
        build_consent_evidence(consent_id=SECOND_CONSENT_ID, sale_id=OTHER_SALE_ID),
        build_consent_idempotency("consent-key-0002"),
    )
    assert second_first.previous_record_hash == GENESIS_PREVIOUS_RECORD_HASH
    with pytest.raises(ConsentRecordChainConflictError):
        unit_of_work.consent_records.append(second_first)


def test_a_record_for_an_unknown_sale_raises_the_database_error(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Only uniqueness becomes a typed error; a broken foreign key is a bug and stays one."""
    store_sales_and_session(session_factory, fixed_clock)
    with (
        pytest.raises(IntegrityError, match="fk_consent_record_sale_id_sale"),
        SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work,
    ):
        unit_of_work.consent_records.append(
            build_first_consent_record(sale_id="01JCSALE000000000000000099")
        )


@pytest.mark.parametrize(
    "modifying_statement",
    [
        "UPDATE consent_record SET phone_last_two_digits = '43' WHERE id = :id",
        "DELETE FROM consent_record WHERE id = :id",
        "TRUNCATE consent_record",
    ],
)
def test_raw_sql_modifying_consent_record_is_rejected_by_trigger(
    unit_of_work: SqlAlchemyUnitOfWork, database_connection: Connection, modifying_statement: str
) -> None:
    """Even SQL that bypasses the repository cannot change or remove consent evidence."""
    first_record = build_first_consent_record()
    unit_of_work.consent_records.append(first_record)
    with (
        pytest.raises(ProgrammingError, match="consent_record is append-only"),
        database_connection.begin_nested(),
    ):
        database_connection.execute(text(modifying_statement), {"id": first_record.id})
    assert unit_of_work.consent_records.list_in_order() == (first_record,)


def test_a_row_written_around_the_repository_with_a_wrong_hash_is_found_by_verification(
    unit_of_work: SqlAlchemyUnitOfWork, database_connection: Connection
) -> None:
    """A forged row still loads, so verify_consent_record_chain can report where it is."""
    first_record = build_first_consent_record()
    unit_of_work.consent_records.append(first_record)
    forged_record = replace(build_second_record(first_record), record_hash="f" * 64)
    database_connection.execute(
        text(
            "INSERT INTO consent_record SELECT :id, 2, :sale_id, customer_session_id,"
            " consent_reference, plan_snapshot, '43', phone_hash, language,"
            " cooling_off_wording_version, consented_at, :previous_hash, :record_hash,"
            " 'forged-key', request_fingerprint, created_at"
            " FROM consent_record WHERE id = :first_id"
        ),
        {
            "id": forged_record.id,
            "sale_id": OTHER_SALE_ID,
            "previous_hash": first_record.record_hash,
            "record_hash": forged_record.record_hash,
            "first_id": first_record.id,
        },
    )
    verification = verify_consent_record_chain(unit_of_work.consent_records.list_in_order())
    assert verification.first_broken_index == 1


@pytest.mark.parametrize(
    ("chain_position", "previous_record_hash", "phone_last_two_digits"),
    [(2, "0" * 64, "42"), (1, "a" * 64, "42"), (1, "0" * 64, "4X")],
    ids=["genesis-link-not-first", "first-without-genesis-link", "phone-not-two-digits"],
)
def test_database_checks_the_genesis_link_and_phone_digits(
    unit_of_work: SqlAlchemyUnitOfWork,
    database_connection: Connection,
    chain_position: int,
    previous_record_hash: str,
    phone_last_two_digits: str,
) -> None:
    """The CHECK constraints back the domain rules for raw inserts too."""
    with (
        pytest.raises(IntegrityError, match="ck_consent_record"),
        database_connection.begin_nested(),
    ):
        database_connection.execute(
            text(
                "INSERT INTO consent_record VALUES (:id, :position, :sale_id, :session_id,"
                " 'EMI-2611-0042', '{}'::jsonb, :digits, :phone_hash, 'en', 'v1', now(),"
                " :previous_hash, :record_hash, 'raw-key', :fingerprint, now())"
            ),
            {
                "id": "01JCCONSENTRAW000000000001",
                "position": chain_position,
                "sale_id": SALE_ID,
                "session_id": build_consent_evidence().customer_session_id,
                "digits": phone_last_two_digits,
                "phone_hash": "c" * 64,
                "previous_hash": previous_record_hash,
                "record_hash": "e" * 64,
                "fingerprint": "d" * 64,
            },
        )
    assert unit_of_work.consent_records.list_in_order() == ()
