"""Integration tests for ReportQueryRepository: cohort counts, budget ranges and missed sales."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.budget_buckets import BUDGET_BUCKET_BOUNDARIES
from emi_copilot.domain.reports.missed_sales import MissedSalesTally
from emi_copilot.domain.sales import SaleStatus, SessionCode
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.fixed_clock import FixedClock
from tests.merchant_builders import (
    MERCHANT_ID,
    OTHER_MERCHANT_ID,
    build_catalogue_product,
    build_merchant,
)
from tests.sale_builders import PRODUCT_ID, SALE_STARTED_AT, build_sale

pytestmark = pytest.mark.integration

PERIOD_STARTS_AT = SALE_STARTED_AT
PERIOD_ENDS_AT = SALE_STARTED_AT + timedelta(days=1)
OTHER_PRODUCT_ID = "01JCPRODUCT000000000000002"
OTHER_SHOP_PRODUCT_ID = "01JCPRODUCT000000000000003"
STAGES_UP_TO = {
    FunnelStage.STARTED: (FunnelStage.STARTED,),
    FunnelStage.BUDGET_TOLD: (FunnelStage.STARTED, FunnelStage.BUDGET_TOLD),
    FunnelStage.PLANS_VIEWED: (
        FunnelStage.STARTED,
        FunnelStage.BUDGET_TOLD,
        FunnelStage.PLANS_VIEWED,
    ),
    FunnelStage.AGREED: (
        FunnelStage.STARTED,
        FunnelStage.BUDGET_TOLD,
        FunnelStage.PLANS_VIEWED,
        FunnelStage.AGREED,
    ),
}


class ReportFixture:
    """Stores two shops' sales with the stages and budgets each test needs."""

    def __init__(self, session_factory: sessionmaker[Session], clock: FixedClock) -> None:
        """Stores both shops and their products."""
        self._session_factory = session_factory
        self._clock = clock
        self._sale_number = 0
        with self.open_unit_of_work() as unit_of_work:
            unit_of_work.merchants.add(build_merchant())
            unit_of_work.merchants.add(build_merchant(id=OTHER_MERCHANT_ID, shop_code="SHOP-0002"))
            unit_of_work.products.add(build_catalogue_product())
            unit_of_work.products.add(
                build_catalogue_product(
                    id=OTHER_PRODUCT_ID,
                    name="Example phone, 64 GB",
                    list_price=Money.from_rupees("18000"),
                    gateway_product_id="product-synthetic-2",
                )
            )
            unit_of_work.products.add(
                build_catalogue_product(
                    id=OTHER_SHOP_PRODUCT_ID,
                    merchant_id=OTHER_MERCHANT_ID,
                    gateway_product_id="product-synthetic-3",
                )
            )

    def open_unit_of_work(self) -> SqlAlchemyUnitOfWork:
        """Opens a fresh unit of work on the test database."""
        return SqlAlchemyUnitOfWork(self._session_factory, self._clock)

    def store_sale(
        self,
        last_stage: FunnelStage,
        budget_in_rupees: str | None = None,
        *,
        merchant_id: str = MERCHANT_ID,
        product_id: str = PRODUCT_ID,
        started_at: datetime = SALE_STARTED_AT,
    ) -> None:
        """Stores an expired sale that reached every stage up to last_stage."""
        self._sale_number += 1
        sale_id = f"01JCREPORTSALE{self._sale_number:012d}"
        with self.open_unit_of_work() as unit_of_work:
            unit_of_work.sales.add(
                build_sale(
                    id=sale_id,
                    merchant_id=merchant_id,
                    product_id=product_id,
                    session_code=SessionCode(f"{self._sale_number:04d}"),
                    status=SaleStatus.EXPIRED,
                    started_at=started_at,
                    status_changed_at=started_at,
                )
            )
            for stage_number, stage in enumerate(STAGES_UP_TO[last_stage]):
                unit_of_work.funnel_events.append(
                    FunnelEvent(
                        id=f"01JCREPORTEVENT{self._sale_number:08d}{stage_number:03d}",
                        sale_id=sale_id,
                        merchant_id=merchant_id,
                        stage=stage,
                        occurred_at=started_at + timedelta(minutes=stage_number),
                        monthly_budget=(
                            Money.from_rupees(budget_in_rupees or "4000")
                            if stage is FunnelStage.BUDGET_TOLD
                            else None
                        ),
                    )
                )


@pytest.fixture
def report_fixture(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> ReportFixture:
    """Two shops with products and no sales yet."""
    return ReportFixture(session_factory, fixed_clock)


def test_stage_counts_count_the_periods_cohort_and_equal_independent_count_queries(
    report_fixture: ReportFixture, database_connection: Connection
) -> None:
    """Sales started before or after the period, and another shop's, are not counted."""
    report_fixture.store_sale(FunnelStage.STARTED)
    report_fixture.store_sale(FunnelStage.PLANS_VIEWED, "3200")
    report_fixture.store_sale(FunnelStage.AGREED, "4100")
    report_fixture.store_sale(FunnelStage.AGREED, started_at=PERIOD_ENDS_AT)
    report_fixture.store_sale(
        FunnelStage.AGREED, started_at=PERIOD_STARTS_AT - timedelta(microseconds=1)
    )
    report_fixture.store_sale(
        FunnelStage.AGREED, merchant_id=OTHER_MERCHANT_ID, product_id=OTHER_SHOP_PRODUCT_ID
    )
    with report_fixture.open_unit_of_work() as unit_of_work:
        counts = unit_of_work.report_queries.count_sales_reaching_each_stage(
            MERCHANT_ID, PERIOD_STARTS_AT, PERIOD_ENDS_AT
        )
    independent_counts: dict[str, int] = dict(
        database_connection.execute(
            text(
                "SELECT f.stage, count(*) FROM funnel_event f JOIN sale s ON s.id = f.sale_id"
                " WHERE s.merchant_id = :merchant_id AND s.started_at >= :starts_at"
                " AND s.started_at < :ends_at GROUP BY f.stage"
            ),
            {"merchant_id": MERCHANT_ID, "starts_at": PERIOD_STARTS_AT, "ends_at": PERIOD_ENDS_AT},
        ).all()
    )
    assert {stage.value: count for stage, count in counts.items()} == independent_counts
    assert counts == {
        FunnelStage.STARTED: 3,
        FunnelStage.BUDGET_TOLD: 2,
        FunnelStage.PLANS_VIEWED: 2,
        FunnelStage.AGREED: 1,
    }


def test_budget_ranges_include_their_lower_boundary(report_fixture: ReportFixture) -> None:
    """₹2,499.99 is under ₹2,500; exactly ₹2,500 and exactly ₹3,000 start their ranges."""
    for budget_in_rupees in ("2499.99", "2500", "2999.99", "3000", "3999.99", "4000", "90000"):
        report_fixture.store_sale(FunnelStage.BUDGET_TOLD, budget_in_rupees)
    report_fixture.store_sale(
        FunnelStage.BUDGET_TOLD,
        "2000",
        merchant_id=OTHER_MERCHANT_ID,
        product_id=OTHER_SHOP_PRODUCT_ID,
    )
    with report_fixture.open_unit_of_work() as unit_of_work:
        counts = unit_of_work.report_queries.count_budgets_per_range(
            MERCHANT_ID, PERIOD_STARTS_AT, PERIOD_ENDS_AT, BUDGET_BUCKET_BOUNDARIES
        )
    assert counts == (1, 2, 1, 1, 2)


def test_no_budgets_give_a_zero_for_every_range(report_fixture: ReportFixture) -> None:
    """The empty shop's shape: five zeros."""
    with report_fixture.open_unit_of_work() as unit_of_work:
        counts = unit_of_work.report_queries.count_budgets_per_range(
            MERCHANT_ID, PERIOD_STARTS_AT, PERIOD_ENDS_AT, BUDGET_BUCKET_BOUNDARIES
        )
    assert counts == (0, 0, 0, 0, 0)


def test_missed_sales_are_unagreed_budgets_strictly_below_the_products_threshold(
    report_fixture: ReportFixture, database_connection: Connection
) -> None:
    """A budget equal to the threshold fits it; agreed or budget-less sales are not missed."""
    report_fixture.store_sale(FunnelStage.PLANS_VIEWED, "2900")
    report_fixture.store_sale(FunnelStage.BUDGET_TOLD, "2400")
    report_fixture.store_sale(FunnelStage.PLANS_VIEWED, "3666.67")
    report_fixture.store_sale(FunnelStage.AGREED, "2000")
    report_fixture.store_sale(FunnelStage.STARTED)
    report_fixture.store_sale(FunnelStage.PLANS_VIEWED, "2999.99", product_id=OTHER_PRODUCT_ID)
    report_fixture.store_sale(FunnelStage.PLANS_VIEWED, "3000", product_id=OTHER_PRODUCT_ID)
    report_fixture.store_sale(
        FunnelStage.PLANS_VIEWED,
        "100",
        merchant_id=OTHER_MERCHANT_ID,
        product_id=OTHER_SHOP_PRODUCT_ID,
    )
    thresholds = {
        PRODUCT_ID: Money.from_rupees("3666.67"),
        OTHER_PRODUCT_ID: Money.from_rupees("3000"),
        OTHER_SHOP_PRODUCT_ID: Money.from_rupees("3666.67"),
    }
    with report_fixture.open_unit_of_work() as unit_of_work:
        tallies = unit_of_work.report_queries.tally_missed_sales(
            MERCHANT_ID, PERIOD_STARTS_AT, PERIOD_ENDS_AT, thresholds
        )
        no_thresholds = unit_of_work.report_queries.tally_missed_sales(
            MERCHANT_ID, PERIOD_STARTS_AT, PERIOD_ENDS_AT, {}
        )
    independent_count = database_connection.execute(
        text(
            "SELECT count(*) FROM sale s JOIN funnel_event b ON b.sale_id = s.id"
            " AND b.stage = 'BUDGET_TOLD' WHERE s.merchant_id = :merchant_id"
            " AND s.product_id = :product_id AND b.monthly_budget_in_paise < 366667"
            " AND NOT EXISTS (SELECT 1 FROM funnel_event a WHERE a.sale_id = s.id"
            " AND a.stage = 'AGREED')"
        ),
        {"merchant_id": MERCHANT_ID, "product_id": PRODUCT_ID},
    ).scalar_one()
    assert tallies == {
        PRODUCT_ID: MissedSalesTally(2, Money.from_rupees("2900")),
        OTHER_PRODUCT_ID: MissedSalesTally(1, Money.from_rupees("2999.99")),
    }
    assert independent_count == 2
    assert no_thresholds == {}


def test_has_any_for_merchant_tells_shops_with_sales_apart(report_fixture: ReportFixture) -> None:
    """The seed uses this to leave a shop's existing history alone."""
    report_fixture.store_sale(FunnelStage.STARTED)
    with report_fixture.open_unit_of_work() as unit_of_work:
        assert unit_of_work.sales.has_any_for_merchant(MERCHANT_ID) is True
        assert unit_of_work.sales.has_any_for_merchant(OTHER_MERCHANT_ID) is False
