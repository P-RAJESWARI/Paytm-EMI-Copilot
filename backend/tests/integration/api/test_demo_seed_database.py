"""The demo seed on PostgreSQL: idempotent, and its shop pairs and lists the M2 offer counts."""

from functools import partial

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from scripts.seed_demo_data import seed_demo_merchant, seed_report_history
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import ApiHarness

pytestmark = pytest.mark.integration

SYNTHETIC_PIN = "135790"


def count_rows(session_factory: sessionmaker[Session], table_name: str) -> int:
    """Counts the rows of one of the seeded tables."""
    with session_factory() as session:
        return int(session.execute(text(f"SELECT count(*) FROM {table_name}")).scalar_one())  # noqa: S608 - fixed table names


def test_seed_demo_merchant_run_twice_stores_one_shop_and_three_products(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Re-running the seed duplicates nothing."""
    unit_of_work_factory = partial(SqlAlchemyUnitOfWork, session_factory, fixed_clock)
    seed_demo_merchant(unit_of_work_factory, SYNTHETIC_PIN)
    seed_demo_merchant(unit_of_work_factory, SYNTHETIC_PIN)
    assert count_rows(session_factory, "merchant") == 1
    assert count_rows(session_factory, "product") == 3


def test_seeded_demo_shop_pairs_with_the_pin_and_lists_the_m2_offer_counts(
    mock_api: ApiHarness,
) -> None:
    """RAVI-0193 pairs with DEMO_MERCHANT_PIN; its products, dearest first, show 3, 2, 1 plans."""
    seed_demo_merchant(
        partial(SqlAlchemyUnitOfWork, mock_api.session_factory, mock_api.clock), SYNTHETIC_PIN
    )
    pairing_response = mock_api.client.post(
        "/api/v1/merchants/pairing", json={"shopId": "RAVI-0193", "pin": SYNTHETIC_PIN}
    )
    assert pairing_response.status_code == 201
    assert pairing_response.json()["merchant"]["shopName"] == "Ravi Electronics"
    products_response = mock_api.client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {pairing_response.json()['accessToken']}"},
    )
    assert [
        (product["name"], product["listPriceInPaise"], product["planCount"])
        for product in products_response.json()["products"]
    ] == [
        ("Example phone, 128 GB", 2_200_000, 3),
        ("Example phone, 64 GB", 1_800_000, 2),
        ("Example earbuds", 249_900, 1),
    ]


def test_seed_report_history_run_twice_stores_the_121_sales_once(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """The step writes the design week once; a shop with sales is left alone.

    121 sales: the 120 the design week's reports count, and 4821 still choosing at the counter.
    """
    unit_of_work_factory = partial(SqlAlchemyUnitOfWork, session_factory, fixed_clock)
    seed_demo_merchant(unit_of_work_factory, SYNTHETIC_PIN)
    seed_report_history(unit_of_work_factory, SYNTHETIC_PIN)
    seed_report_history(unit_of_work_factory, SYNTHETIC_PIN)
    assert count_rows(session_factory, "sale") == 121
    assert count_rows(session_factory, "funnel_event") == 121 + 96 + 88 + 51 + 44
