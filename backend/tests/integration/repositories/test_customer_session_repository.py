"""Integration tests for CustomerSessionRepository and OtpChallengeRepository on PostgreSQL."""

from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.customer_sessions import ComfortCheckStatus, CustomerLanguage
from emi_copilot.domain.errors import CustomerSessionNotFoundError, OtpNotRequestedError
from emi_copilot.domain.money import Money
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.consent_builders import (
    CUSTOMER_SESSION_ID,
    SESSION_STARTED_AT,
    SYNTHETIC_SESSION_TOKEN_HASH,
    build_customer_session,
    build_otp_challenge,
)
from tests.fixed_clock import FixedClock
from tests.integration.repositories.customer_flow_storage import (
    OTHER_SALE_ID,
    store_sales_and_session,
)
from tests.sale_builders import SALE_ID

pytestmark = pytest.mark.integration

SECOND_SESSION_ID = "01JCSESSION000000000000002"
LATER = SESSION_STARTED_AT + timedelta(minutes=2)


@pytest.fixture
def unit_of_work(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> Iterator[SqlAlchemyUnitOfWork]:
    """Stores the sample sales and session, then opens one unit of work for the test."""
    store_sales_and_session(session_factory, fixed_clock)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as opened_unit_of_work:
        yield opened_unit_of_work


def test_find_by_token_hash_returns_the_stored_session_in_utc(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """A session round-trips unchanged; an unknown hash finds nothing."""
    assert unit_of_work.customer_sessions.find_by_token_hash(SYNTHETIC_SESSION_TOKEN_HASH) == (
        build_customer_session()
    )
    assert unit_of_work.customer_sessions.find_by_token_hash("f" * 64) is None


def test_update_saves_budget_comfort_choice_language_and_revocation(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Each mutable field is stored, the budget as integer paise."""
    changed_session = (
        build_customer_session()
        .confirm_budget(Money.from_rupees("3000"))
        .record_comfort_check_choice(has_consented=True)
        .choose_language(CustomerLanguage.TAMIL)
        .revoke(LATER)
    )
    assert unit_of_work.customer_sessions.update(changed_session) == changed_session
    stored_session = unit_of_work.customer_sessions.find_by_id_for_update(CUSTOMER_SESSION_ID)
    assert stored_session == changed_session
    assert stored_session is not None
    assert stored_session.comfort_check_status is ComfortCheckStatus.COMPLETED


def test_update_of_an_unknown_session_raises_not_found(unit_of_work: SqlAlchemyUnitOfWork) -> None:
    """Only a stored session can be updated."""
    with pytest.raises(CustomerSessionNotFoundError):
        unit_of_work.customer_sessions.update(build_customer_session(id=SECOND_SESSION_ID))


def test_list_unrevoked_for_sale_lists_only_that_sales_live_sessions_oldest_first(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Revoked sessions and other sales' sessions are left out."""
    second_session = build_customer_session(
        id=SECOND_SESSION_ID,
        token_hash="e" * 64,
        created_at=LATER,
        expires_at=LATER + timedelta(minutes=30),
    )
    other_sale_session = build_customer_session(
        id="01JCSESSION000000000000003", sale_id=OTHER_SALE_ID, token_hash="9" * 64
    )
    unit_of_work.customer_sessions.add(second_session)
    unit_of_work.customer_sessions.add(other_sale_session)
    assert unit_of_work.customer_sessions.list_unrevoked_for_sale_for_update(SALE_ID) == (
        build_customer_session(),
        second_session,
    )
    unit_of_work.customer_sessions.update(build_customer_session().revoke(LATER))
    assert unit_of_work.customer_sessions.list_unrevoked_for_sale_for_update(SALE_ID) == (
        second_session,
    )


def test_database_refuses_a_second_session_with_the_same_token_hash(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Token hashes are unique, so one token can never open two sessions."""
    store_sales_and_session(session_factory, fixed_clock)
    with (
        pytest.raises(IntegrityError, match="uq_customer_session_token_hash"),
        SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work,
    ):
        unit_of_work.customer_sessions.add(build_customer_session(id=SECOND_SESSION_ID))


def test_otp_challenge_round_trips_and_the_latest_is_found(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """A resent code is the latest one; attempts and verification are saved."""
    first_challenge = build_otp_challenge()
    resent_challenge = build_otp_challenge(
        id="01JCOTP0000000000000000002",
        code_hash="7" * 64,
        created_at=LATER,
        expires_at=LATER + timedelta(minutes=5),
        resend_available_at=LATER + timedelta(seconds=30),
    )
    assert (
        unit_of_work.otp_challenges.find_latest_for_session_for_update(CUSTOMER_SESSION_ID) is None
    )
    unit_of_work.otp_challenges.add(first_challenge)
    unit_of_work.otp_challenges.add(resent_challenge)
    latest = unit_of_work.otp_challenges.find_latest_for_session_for_update(CUSTOMER_SESSION_ID)
    assert latest == resent_challenge
    verified_challenge = resent_challenge.record_wrong_attempt().mark_verified(LATER)
    assert unit_of_work.otp_challenges.update(verified_challenge) == verified_challenge
    assert (
        unit_of_work.otp_challenges.find_latest_for_session_for_update(CUSTOMER_SESSION_ID)
        == verified_challenge
    )


def test_otp_challenge_update_of_an_unknown_challenge_raises(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Only a stored challenge can be updated."""
    with pytest.raises(OtpNotRequestedError):
        unit_of_work.otp_challenges.update(build_otp_challenge())


def test_database_refuses_negative_attempts_left(
    unit_of_work: SqlAlchemyUnitOfWork, database_connection: Connection
) -> None:
    """The CHECK constraint backs the domain rule."""
    with (
        pytest.raises(IntegrityError, match="ck_consent_otp_challenge_attempts_remaining"),
        database_connection.begin_nested(),
    ):
        database_connection.execute(
            text(
                "INSERT INTO consent_otp_challenge VALUES ('01JCOTPRAW0000000000000001', :session,"
                " :code_hash, -1, now(), now(), NULL, now(), now())"
            ),
            {"session": CUSTOMER_SESSION_ID, "code_hash": "b" * 64},
        )
    assert (
        unit_of_work.otp_challenges.find_latest_for_session_for_update(CUSTOMER_SESSION_ID) is None
    )
