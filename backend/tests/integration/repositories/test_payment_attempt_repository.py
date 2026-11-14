"""Integration tests for PaymentAttemptRepository against the PostgreSQL test database."""

from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.errors import PaymentAttemptAlreadyExistsError, PaymentAttemptNotFoundError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PaymentAttemptStatus, PaymentLinkFailureCode
from emi_copilot.repositories.payment_attempt_repository import PaymentAttemptRepository
from tests.fixed_clock import FixedClock
from tests.payment_builders import (
    CREATED_AT,
    build_payment_attempt,
    build_standard_offer_snapshot,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Opens one session for the test; its changes vanish with the outer transaction."""
    with session_factory() as session:
        yield session


@pytest.fixture
def repository(session: Session, fixed_clock: FixedClock) -> PaymentAttemptRepository:
    """Builds the repository on the test session and the fixed clock."""
    return PaymentAttemptRepository(session, fixed_clock)


def test_add_then_find_by_idempotency_key_returns_equal_attempt(
    repository: PaymentAttemptRepository, session: Session
) -> None:
    """A stored attempt comes back unchanged: Money to the paisa, snapshot and UTC timestamps."""
    payment_attempt = build_payment_attempt(offer_snapshot=build_standard_offer_snapshot())
    repository.add(payment_attempt)
    session.expunge_all()
    assert repository.find_by_idempotency_key(payment_attempt.idempotency_key) == payment_attempt


def test_add_stores_amount_as_integer_paise_and_snapshot_as_json(
    repository: PaymentAttemptRepository, session: Session
) -> None:
    """The row holds BigInteger paise and the snapshot's integer-paise JSON, never floats."""
    payment_attempt = build_payment_attempt(amount=Money.from_rupees("22000.01"))
    repository.add(payment_attempt)
    stored_row = session.execute(
        text(
            "SELECT amount_in_paise, offer_snapshot -> 'total_payable_in_paise' AS total_payable,"
            " jsonb_typeof(offer_snapshot -> 'total_payable_in_paise') AS total_payable_type"
            " FROM payment_attempt WHERE id = :id"
        ),
        {"id": payment_attempt.id},
    ).one()
    assert stored_row.amount_in_paise == 2_200_001
    assert stored_row.total_payable == 2_200_000
    assert stored_row.total_payable_type == "number"


def test_find_by_order_id_returns_matching_attempt_only(
    repository: PaymentAttemptRepository,
) -> None:
    """Lookup by gateway order id finds that attempt and nothing for an unknown order id."""
    first_attempt = build_payment_attempt(1)
    repository.add(first_attempt)
    repository.add(build_payment_attempt(2))
    assert repository.find_by_order_id(first_attempt.order_id) == first_attempt
    assert repository.find_by_order_id("ORDER-NOT-STORED") is None


def test_find_by_idempotency_key_with_unknown_key_returns_none(
    repository: PaymentAttemptRepository,
) -> None:
    """An unused Idempotency-Key finds nothing, so the service knows to create an attempt."""
    assert repository.find_by_idempotency_key("idempotency-key-not-stored") is None


@pytest.mark.parametrize(
    ("duplicated_field", "expected_constraint"),
    [
        ("idempotency_key", "uq_payment_attempt_idempotency_key"),
        ("order_id", "uq_payment_attempt_order_id"),
        ("id", "pk_payment_attempt"),
    ],
)
def test_add_with_duplicate_unique_value_raises_already_exists_and_keeps_session_usable(
    repository: PaymentAttemptRepository, duplicated_field: str, expected_constraint: str
) -> None:
    """A racing duplicate raises a typed error; the first attempt can still be read afterwards."""
    first_attempt = build_payment_attempt(1)
    repository.add(first_attempt)
    racing_attempt = replace(
        build_payment_attempt(2), **{duplicated_field: getattr(first_attempt, duplicated_field)}
    )
    with pytest.raises(PaymentAttemptAlreadyExistsError, match=expected_constraint):
        repository.add(racing_attempt)
    assert repository.find_by_idempotency_key(first_attempt.idempotency_key) == first_attempt


def test_add_with_row_violating_a_check_constraint_reraises_integrity_error(
    repository: PaymentAttemptRepository,
) -> None:
    """Only duplicates become the typed error; other integrity failures are not disguised."""
    payment_attempt = build_payment_attempt()
    object.__setattr__(payment_attempt, "amount", Money.from_paise(0))
    with pytest.raises(IntegrityError, match="ck_payment_attempt_amount_in_paise_positive"):
        repository.add(payment_attempt)


def test_update_saves_mutable_fields_and_stamps_updated_at_from_clock(
    repository: PaymentAttemptRepository, session: Session, fixed_clock: FixedClock
) -> None:
    """Status and gateway references are saved; updated_at comes from the injected clock."""
    payment_attempt = build_payment_attempt()
    repository.add(payment_attempt)
    fixed_clock.advance(timedelta(seconds=3))
    link_created_attempt = replace(
        payment_attempt,
        status=PaymentAttemptStatus.LINK_CREATED,
        gateway_link_id="link-sample-0001",
        payment_link_url="https://example.invalid/pay/link-sample-0001",
        gateway_transaction_id="transaction-sample-0001",
    )
    stored_attempt = repository.update(link_created_attempt)
    session.expunge_all()
    expected_attempt = replace(link_created_attempt, updated_at=CREATED_AT + timedelta(seconds=3))
    assert stored_attempt == expected_attempt
    assert repository.find_by_order_id(payment_attempt.order_id) == expected_attempt


def test_update_ignores_changes_to_immutable_fields(
    repository: PaymentAttemptRepository,
) -> None:
    """The amount, keys and snapshot fixed at creation cannot be rewritten through update."""
    payment_attempt = build_payment_attempt()
    repository.add(payment_attempt)
    rewritten_attempt = replace(
        payment_attempt,
        amount=Money.from_rupees("1"),
        idempotency_key="idempotency-key-rewritten",
        offer_snapshot=build_standard_offer_snapshot(),
    )
    stored_attempt = repository.update(rewritten_attempt)
    assert stored_attempt == payment_attempt


def test_update_of_unknown_attempt_raises_payment_attempt_not_found_error(
    repository: PaymentAttemptRepository,
) -> None:
    """Updating an attempt that was never stored is a typed error, not a silent insert."""
    with pytest.raises(PaymentAttemptNotFoundError):
        repository.update(build_payment_attempt())


def test_update_saves_the_failure_code_of_a_failed_attempt(
    repository: PaymentAttemptRepository, session: Session
) -> None:
    """LINK_CREATION_FAILED and its code are stored and read back as the domain enum."""
    payment_attempt = build_payment_attempt()
    repository.add(payment_attempt)
    failed_attempt = replace(
        payment_attempt,
        status=PaymentAttemptStatus.LINK_CREATION_FAILED,
        failure_code=PaymentLinkFailureCode.GATEWAY_INTERNAL_ERROR,
    )
    repository.update(failed_attempt)
    session.expunge_all()
    stored_attempt = repository.find_by_order_id(payment_attempt.order_id)
    assert stored_attempt is not None
    assert stored_attempt.failure_code is PaymentLinkFailureCode.GATEWAY_INTERNAL_ERROR
    stored_code = session.execute(
        text("SELECT failure_code FROM payment_attempt WHERE id = :id"), {"id": payment_attempt.id}
    ).scalar_one()
    assert stored_code == "GATEWAY_INTERNAL_ERROR"


def test_failure_code_check_constraint_rejects_an_unknown_code(
    repository: PaymentAttemptRepository, session: Session
) -> None:
    """The database refuses a failure code the code base does not know."""
    payment_attempt = build_payment_attempt()
    repository.add(payment_attempt)
    with pytest.raises(IntegrityError, match="ck_payment_attempt_failure_code_known"):
        session.execute(
            text("UPDATE payment_attempt SET failure_code = 'SOMETHING_ELSE' WHERE id = :id"),
            {"id": payment_attempt.id},
        )


def test_find_by_order_id_for_update_returns_the_attempt_or_none(
    repository: PaymentAttemptRepository,
) -> None:
    """The locking lookup finds the same attempt as the plain one, and None for an unknown id."""
    payment_attempt = build_payment_attempt()
    repository.add(payment_attempt)
    assert repository.find_by_order_id_for_update(payment_attempt.order_id) == payment_attempt
    assert repository.find_by_order_id_for_update("ORDER-NOT-STORED") is None
