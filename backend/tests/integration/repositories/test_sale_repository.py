"""Integration tests for SaleRepository on PostgreSQL: scoping, windows, locks and constraints."""

from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.errors import SaleNotFoundError
from emi_copilot.domain.sales import Sale, SaleIdempotency, SaleStatus, SessionCode
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.fixed_clock import FixedClock
from tests.merchant_builders import (
    MERCHANT_ID,
    OTHER_MERCHANT_ID,
    build_catalogue_product,
    build_merchant,
)
from tests.payment_builders import build_payment_attempt
from tests.sale_builders import (
    PRODUCT_ID,
    SALE_STARTED_AT,
    build_qr_token_state,
    build_sale,
    build_standard_chosen_plan,
)

pytestmark = pytest.mark.integration

OTHER_PRODUCT_ID = "01JCPRODUCT000000000000002"


def numbered_sale(sale_number: int, **overrides: object) -> Sale:
    """A sale whose id and code are unique per number; its status changed when it started."""
    fields: dict[str, object] = {
        "id": f"01JCSALE{sale_number:018d}",
        "session_code": SessionCode(f"{sale_number:04d}"),
    }
    fields.update(overrides)
    fields.setdefault("status_changed_at", fields.get("started_at", SALE_STARTED_AT))
    return build_sale(**fields)


def store_two_shops(session_factory: sessionmaker[Session], fixed_clock: FixedClock) -> None:
    """Commits two shops with one product each; they vanish with the outer transaction."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as setup_unit_of_work:
        setup_unit_of_work.merchants.add(build_merchant())
        setup_unit_of_work.merchants.add(
            build_merchant(id=OTHER_MERCHANT_ID, shop_code="SHOP-0002")
        )
        setup_unit_of_work.products.add(build_catalogue_product())
        setup_unit_of_work.products.add(
            build_catalogue_product(id=OTHER_PRODUCT_ID, merchant_id=OTHER_MERCHANT_ID)
        )


def add_in_one_unit_of_work(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock, *sales: Sale
) -> None:
    """Adds the sales in one unit of work, which rolls back if any insert fails."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        for sale in sales:
            unit_of_work.sales.add(sale)


@pytest.fixture
def stored_shops(session_factory: sessionmaker[Session], fixed_clock: FixedClock) -> None:
    """Stores the two shops for a test that opens its own units of work."""
    store_two_shops(session_factory, fixed_clock)


@pytest.fixture
def unit_of_work(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> Iterator[SqlAlchemyUnitOfWork]:
    """Stores the two shops, then opens one unit of work for the test."""
    store_two_shops(session_factory, fixed_clock)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as opened_unit_of_work:
        yield opened_unit_of_work


def test_add_then_find_returns_an_equal_sale_with_plan_and_idempotency(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Price, code, plan snapshot, QR state and the Idempotency-Key all round-trip."""
    sale = build_sale(
        status=SaleStatus.READY_TO_PAY,
        chosen_plan=build_standard_chosen_plan(),
        qr_token=build_qr_token_state(exchanged_at=SALE_STARTED_AT),
        idempotency=SaleIdempotency("sale-key-0001", "f" * 64),
    )
    unit_of_work.sales.add(sale)
    assert unit_of_work.sales.find_by_id_for_merchant(MERCHANT_ID, sale.id) == sale
    assert unit_of_work.sales.find_by_id_for_merchant_for_update(MERCHANT_ID, sale.id) == sale
    assert unit_of_work.sales.find_by_id_for_update(sale.id) == sale
    assert (
        unit_of_work.sales.find_by_idempotency_key_for_merchant(MERCHANT_ID, "sale-key-0001")
        == sale
    )


def test_merchant_scoped_reads_never_return_another_shops_sale(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Another shop asking for this sale, or for its key, gets nothing."""
    sale = build_sale(idempotency=SaleIdempotency("sale-key-0001", "f" * 64))
    unit_of_work.sales.add(sale)
    assert unit_of_work.sales.find_by_id_for_merchant(OTHER_MERCHANT_ID, sale.id) is None
    assert unit_of_work.sales.find_by_id_for_merchant_for_update(OTHER_MERCHANT_ID, sale.id) is None
    assert (
        unit_of_work.sales.find_by_idempotency_key_for_merchant(OTHER_MERCHANT_ID, "sale-key-0001")
        is None
    )
    assert unit_of_work.sales.list_open_session_codes_for_merchant(OTHER_MERCHANT_ID) == frozenset()


def test_update_saves_status_plan_and_qr_token_and_stamps_updated_at(
    unit_of_work: SqlAlchemyUnitOfWork,
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
) -> None:
    """The mutable fields change; the start and the price never do."""
    sale = build_sale()
    unit_of_work.sales.add(sale)
    fixed_clock.advance(timedelta(minutes=3))
    agreed_sale = sale.agree_to_plan(build_standard_chosen_plan(), fixed_clock.now())
    reissued = replace(agreed_sale, qr_token=build_qr_token_state(nonce_hash="1" * 64))
    assert unit_of_work.sales.update(reissued) == reissued
    with session_factory() as session:
        stored_row = session.execute(
            text("SELECT updated_at, created_at FROM sale WHERE id = :id"), {"id": sale.id}
        ).one()
    assert stored_row.updated_at - stored_row.created_at == timedelta(minutes=3)


def test_update_of_an_unknown_sale_raises_not_found(unit_of_work: SqlAlchemyUnitOfWork) -> None:
    """Saving a sale that was never added is a bug, reported as a typed error."""
    with pytest.raises(SaleNotFoundError):
        unit_of_work.sales.update(build_sale())


def test_list_started_between_is_half_open_newest_first_and_skips_the_excluded_status(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Sales at the window start are in, at the end are out, and EXPIRED ones are left out."""
    window_start = SALE_STARTED_AT
    window_end = SALE_STARTED_AT + timedelta(days=1)
    at_start = numbered_sale(1, started_at=window_start)
    later = numbered_sale(2, started_at=window_start + timedelta(hours=2))
    expired = numbered_sale(3, status=SaleStatus.EXPIRED)
    at_end = numbered_sale(4, started_at=window_end)
    before = numbered_sale(5, started_at=window_start - timedelta(seconds=1))
    for sale in (at_start, later, expired, at_end, before):
        unit_of_work.sales.add(sale)
    assert unit_of_work.sales.list_started_between_for_merchant(
        MERCHANT_ID, window_start, window_end, SaleStatus.EXPIRED
    ) == (later, at_start)


def test_list_choosing_started_by_includes_the_cutoff_and_only_choosing_sales(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """A CHOOSING sale started exactly at the cutoff is listed; agreed and later ones are not."""
    at_cutoff = numbered_sale(1)
    agreed = numbered_sale(2, status=SaleStatus.READY_TO_PAY)
    after_cutoff = numbered_sale(3, started_at=SALE_STARTED_AT + timedelta(microseconds=1))
    for sale in (at_cutoff, agreed, after_cutoff):
        unit_of_work.sales.add(sale)
    assert unit_of_work.sales.list_choosing_started_by_for_merchant_for_update(
        MERCHANT_ID, SALE_STARTED_AT
    ) == (at_cutoff,)


def test_list_open_session_codes_ignores_paid_and_expired_sales(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Codes on CHOOSING, READY_TO_PAY and PAYMENT_NOT_COMPLETED sales are taken, others free."""
    for sale_number, status in enumerate(SaleStatus, start=1):
        unit_of_work.sales.add(numbered_sale(sale_number, status=status))
    assert unit_of_work.sales.list_open_session_codes_for_merchant(MERCHANT_ID) == {
        "0001",
        "0002",
        "0004",
    }


@pytest.mark.usefixtures("stored_shops")
def test_database_refuses_a_second_open_sale_with_the_same_code(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """The partial unique index backs the service's choice of a free code."""
    with pytest.raises(IntegrityError, match="uq_sale_merchant_id_session_code_open"):
        add_in_one_unit_of_work(
            session_factory,
            fixed_clock,
            numbered_sale(1),
            numbered_sale(2, session_code=SessionCode("0001")),
        )


def test_database_allows_a_code_again_once_the_old_sale_is_closed(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """A paid or expired sale's code may be reused, and another shop may use any code."""
    unit_of_work.sales.add(numbered_sale(1, status=SaleStatus.PAID))
    unit_of_work.sales.add(numbered_sale(2, session_code=SessionCode("0001")))
    unit_of_work.sales.add(
        numbered_sale(
            3,
            session_code=SessionCode("0001"),
            merchant_id=OTHER_MERCHANT_ID,
            product_id=OTHER_PRODUCT_ID,
        )
    )
    assert unit_of_work.sales.list_open_session_codes_for_merchant(MERCHANT_ID) == {"0001"}


@pytest.mark.usefixtures("stored_shops")
def test_database_refuses_a_reused_idempotency_key_within_one_shop(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """One shop's key starts one sale; the constraint backs the service's replay lookup."""
    idempotency = SaleIdempotency("sale-key-0001", "f" * 64)
    with pytest.raises(IntegrityError, match="uq_sale_merchant_id_idempotency_key"):
        add_in_one_unit_of_work(
            session_factory,
            fixed_clock,
            numbered_sale(1, idempotency=idempotency),
            numbered_sale(2, idempotency=idempotency),
        )


def test_lock_for_update_locks_the_merchant_row_without_error(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Locking an existing (or unknown) shop row is a plain SELECT ... FOR UPDATE."""
    unit_of_work.merchants.lock_for_update(MERCHANT_ID)
    unit_of_work.merchants.lock_for_update("01JCMERCHANT00000000000099")


def test_payment_attempt_keeps_its_sale_link(unit_of_work: SqlAlchemyUnitOfWork) -> None:
    """payment_attempt.sale_id round-trips, and an attempt may still have no sale."""
    unit_of_work.sales.add(build_sale())
    linked_attempt = build_payment_attempt(1, sale_id=build_sale().id)
    unlinked_attempt = build_payment_attempt(2)
    unit_of_work.payment_attempts.add(linked_attempt)
    unit_of_work.payment_attempts.add(unlinked_attempt)
    assert unit_of_work.payment_attempts.find_by_order_id(linked_attempt.order_id) == linked_attempt
    stored_unlinked = unit_of_work.payment_attempts.find_by_order_id(unlinked_attempt.order_id)
    assert stored_unlinked is not None
    assert stored_unlinked.sale_id is None


def test_product_of_the_sample_sale_is_the_stored_one() -> None:
    """The builders agree on the product id the sale foreign key points at."""
    assert build_catalogue_product().id == PRODUCT_ID
