"""Integration tests for the merchant, device pairing and product repositories on PostgreSQL."""

from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import Row, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.merchants import PinAttemptState
from emi_copilot.domain.money import Money
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.fixed_clock import FixedClock
from tests.merchant_builders import (
    MERCHANT_ID,
    OTHER_MERCHANT_ID,
    PAIRED_AT,
    build_catalogue_product,
    build_device_pairing,
    build_merchant,
)

pytestmark = pytest.mark.integration


def store_two_merchants(session_factory: sessionmaker[Session], clock: FixedClock) -> None:
    """Commits two shops; like every write here, they vanish with the outer transaction."""
    with SqlAlchemyUnitOfWork(session_factory, clock) as unit_of_work:
        unit_of_work.merchants.add(build_merchant())
        unit_of_work.merchants.add(build_merchant(id=OTHER_MERCHANT_ID, shop_code="SHOP-0002"))


@pytest.fixture
def stored_merchants(session_factory: sessionmaker[Session], fixed_clock: FixedClock) -> None:
    """Stores the two shops for a test that opens its own units of work."""
    store_two_merchants(session_factory, fixed_clock)


@pytest.fixture
def unit_of_work(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> Iterator[SqlAlchemyUnitOfWork]:
    """Stores the two shops, then opens one unit of work for the test."""
    store_two_merchants(session_factory, fixed_clock)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as opened_unit_of_work:
        yield opened_unit_of_work


def read_one_row(session_factory: sessionmaker[Session], sql: str, merchant_id: str) -> Row[Any]:
    """Runs raw SQL for one merchant on the test connection, which sees unflushed-to-disk rows."""
    with session_factory() as session:
        return session.execute(text(sql), {"merchant_id": merchant_id}).one()


def test_merchant_add_then_find_returns_equal_merchant(unit_of_work: SqlAlchemyUnitOfWork) -> None:
    """A stored shop comes back unchanged by id and by shop code."""
    assert unit_of_work.merchants.find_by_id(MERCHANT_ID) == build_merchant()
    assert unit_of_work.merchants.find_by_shop_code_for_update("SHOP-0001") == build_merchant()
    assert unit_of_work.merchants.find_by_shop_code_for_update("SHOP-9999") is None
    assert unit_of_work.merchants.find_by_id("01JCMERCHANT00000000000099") is None


def test_merchant_update_saves_attempt_state_and_lock_end_in_utc(
    unit_of_work: SqlAlchemyUnitOfWork,
    fixed_clock: FixedClock,
    session_factory: sessionmaker[Session],
) -> None:
    """The failure count and lock end survive a round trip; updated_at moves with the clock."""
    locked_state = PinAttemptState(consecutive_failure_count=0, locked_until=PAIRED_AT)
    fixed_clock.advance(timedelta(minutes=5))
    unit_of_work.merchants.update(replace(build_merchant(), pin_attempt_state=locked_state))
    assert unit_of_work.merchants.find_by_id(MERCHANT_ID) == replace(
        build_merchant(), pin_attempt_state=locked_state
    )
    timestamps = read_one_row(
        session_factory,
        "SELECT created_at, updated_at FROM merchant WHERE id = :merchant_id",
        MERCHANT_ID,
    )
    assert timestamps.updated_at - timestamps.created_at == timedelta(minutes=5)


def test_merchant_update_of_unknown_merchant_raises(unit_of_work: SqlAlchemyUnitOfWork) -> None:
    """Updating a shop that was never stored is a programming error, reported as typed."""
    with pytest.raises(InvalidMerchantDataError, match="No merchant"):
        unit_of_work.merchants.update(build_merchant(id="01JCMERCHANT00000000000099"))


@pytest.mark.usefixtures("stored_merchants")
def test_merchant_add_with_duplicate_shop_code_is_refused_by_the_database(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Shop codes are unique, so pairing can never match two shops."""
    duplicate_shop = build_merchant(id="01JCMERCHANT00000000000003")
    with (
        pytest.raises(IntegrityError, match="uq_merchant_shop_code"),
        SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work,
    ):
        unit_of_work.merchants.add(duplicate_shop)


def test_device_pairing_add_then_find_by_token_hash_returns_equal_pairing(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """A pairing is found by its token hash only; another hash finds nothing."""
    revoked_pairing = build_device_pairing(revoked_at=PAIRED_AT)
    unit_of_work.device_pairings.add(revoked_pairing)
    assert (
        unit_of_work.device_pairings.find_by_access_token_hash(revoked_pairing.access_token_hash)
        == revoked_pairing
    )
    assert unit_of_work.device_pairings.find_by_access_token_hash("e" * 64) is None


@pytest.mark.usefixtures("stored_merchants")
def test_device_pairing_with_duplicate_token_hash_is_refused_by_the_database(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """A token hash signs in exactly one device."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.device_pairings.add(build_device_pairing())
    second_pairing = build_device_pairing(id="01JCPAIRING000000000000002")
    with (
        pytest.raises(IntegrityError, match="uq_device_pairing_access_token_hash"),
        SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work,
    ):
        unit_of_work.device_pairings.add(second_pairing)


def test_product_list_for_merchant_returns_only_that_merchants_products_by_name(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """Products are sorted by name and another shop's product never appears."""
    phone = build_catalogue_product()
    earbuds = build_catalogue_product(
        id="01JCPRODUCT000000000000002",
        name="Example earbuds",
        list_price=Money.from_paise(249_900),
    )
    other_shops_product = build_catalogue_product(
        id="01JCPRODUCT000000000000003", merchant_id=OTHER_MERCHANT_ID, name="Example phone, 64 GB"
    )
    for product in (phone, earbuds, other_shops_product):
        unit_of_work.products.add(product)
    assert unit_of_work.products.list_for_merchant(MERCHANT_ID) == (earbuds, phone)
    assert unit_of_work.products.list_for_merchant(OTHER_MERCHANT_ID) == (other_shops_product,)


@pytest.mark.parametrize(
    ("search_text", "expected_names"),
    [
        ("PHONE", ["Example phone, 128 GB"]),
        ("example", ["Example earbuds", "Example phone, 128 GB"]),
        ("%", ["100% cotton cover"]),
        ("_", []),
        ("", ["100% cotton cover", "Example earbuds", "Example phone, 128 GB"]),
        (None, ["100% cotton cover", "Example earbuds", "Example phone, 128 GB"]),
    ],
)
def test_product_list_for_merchant_with_search_matches_names_ignoring_case_and_wildcards(
    unit_of_work: SqlAlchemyUnitOfWork, search_text: str | None, expected_names: list[str]
) -> None:
    """The search is a case-blind "contains"; % and _ match only themselves."""
    for index, name in enumerate(("Example phone, 128 GB", "Example earbuds", "100% cotton cover")):
        unit_of_work.products.add(
            build_catalogue_product(id=f"01JCPRODUCT00000000000001{index}", name=name)
        )
    listed_products = unit_of_work.products.list_for_merchant(MERCHANT_ID, search_text)
    assert [product.name for product in listed_products] == expected_names


def test_product_find_by_id_for_merchant_hides_another_merchants_product(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """A product id of another shop finds nothing, exactly like an unknown id."""
    product = build_catalogue_product()
    unit_of_work.products.add(product)
    assert unit_of_work.products.find_by_id_for_merchant(MERCHANT_ID, product.id) == product
    assert unit_of_work.products.find_by_id_for_merchant(OTHER_MERCHANT_ID, product.id) is None
    assert unit_of_work.products.find_by_id_for_merchant(MERCHANT_ID, "unknown") is None


def test_product_find_by_gateway_product_id_for_merchant_is_scoped_to_the_merchant(
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    """The seed's existence check sees only the shop it is seeding."""
    product = build_catalogue_product()
    unit_of_work.products.add(product)
    products = unit_of_work.products
    assert products.find_by_gateway_product_id_for_merchant(MERCHANT_ID, "product-synthetic-1") == (
        product
    )
    assert (
        products.find_by_gateway_product_id_for_merchant(OTHER_MERCHANT_ID, "product-synthetic-1")
        is None
    )


def test_product_stores_list_price_as_integer_paise(
    unit_of_work: SqlAlchemyUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    """The row holds BIGINT paise, not rupees and never a float."""
    unit_of_work.products.add(build_catalogue_product(list_price=Money.from_rupees("2499")))
    stored_row = read_one_row(
        session_factory,
        "SELECT list_price_in_paise, pg_typeof(list_price_in_paise)::text AS column_type"
        " FROM product WHERE merchant_id = :merchant_id",
        MERCHANT_ID,
    )
    assert (stored_row.list_price_in_paise, stored_row.column_type) == (249_900, "bigint")


@pytest.mark.usefixtures("stored_merchants")
def test_product_with_zero_price_is_refused_by_the_database(
    session_factory: sessionmaker[Session],
) -> None:
    """The positive-price CHECK holds even for SQL that bypasses the domain."""
    with (
        pytest.raises(IntegrityError, match="ck_product_list_price_in_paise_positive"),
        session_factory() as session,
    ):
        session.execute(
            text(
                "INSERT INTO product (id, merchant_id, display_name, gateway_product_id,"
                " gateway_brand_id, gateway_category_id, list_price_in_paise, created_at,"
                " updated_at) VALUES ('01JCPRODUCT000000000000009', :merchant_id, 'Free item',"
                " 'p', 'b', 'c', 0, now(), now())"
            ),
            {"merchant_id": MERCHANT_ID},
        )
