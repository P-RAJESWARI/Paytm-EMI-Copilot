"""Missed sales: the per-sale rule, the budget ceiling, the insight product and the card."""

import pytest

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.reports.budget_buckets import build_budget_bucket_report
from emi_copilot.domain.reports.missed_sales import (
    MissedSalesAnalysis,
    MissedSalesReport,
    ProductOffers,
    build_product_insight,
    choose_insight_product,
    find_budget_ceiling,
    find_cheapest_plan_under_ceiling,
    find_lowest_no_extra_cost_offer,
    is_missed_sale,
)
from emi_copilot.domain.reports.small_count_suppression import (
    ReportedCount,
    SmallCountSuppressionPolicy,
)
from tests.report_builders import (
    EARBUDS,
    PHONE_64_GB,
    PHONE_128_GB,
    build_design_missed_sales_analysis,
    build_earbuds_offers,
    build_phone_64_gb_offers,
    build_phone_128_gb_offers,
    build_priced_offer,
    build_product,
    build_product_missed_sales,
)

LOWEST_NO_COST_MONTHLY = Money.from_rupees("3666.67")


@pytest.mark.parametrize(
    ("budget_in_rupees", "has_agreed", "expected_is_missed"),
    [
        ("2900", False, True),
        ("3666.66", False, True),
        ("3666.67", False, False),
        ("4000", False, False),
        ("2900", True, False),
        (None, False, False),
    ],
)
def test_is_missed_sale_needs_a_budget_below_the_lowest_no_cost_monthly_and_no_agreement(
    budget_in_rupees: str | None, has_agreed: bool, expected_is_missed: bool
) -> None:
    """A budget equal to the cheapest no-cost monthly fits that plan, so it is not missed."""
    budget = None if budget_in_rupees is None else Money.from_rupees(budget_in_rupees)
    assert is_missed_sale(budget, has_agreed, LOWEST_NO_COST_MONTHLY) is expected_is_missed


def test_is_missed_sale_is_false_for_a_product_without_a_no_cost_plan() -> None:
    """The earbuds have no plan without extra, so nobody can miss one."""
    assert is_missed_sale(Money.from_rupees("100"), False, None) is False


def test_lowest_no_extra_cost_offer_ignores_plans_with_extra_and_breaks_ties() -> None:
    """Plan A for the 128 GB phone; a tie on monthly goes to the shorter tenure, then the id."""
    assert find_lowest_no_extra_cost_offer(build_earbuds_offers()) is None
    assert (
        find_lowest_no_extra_cost_offer(build_phone_128_gb_offers())
        == (build_phone_128_gb_offers()[0])
    )
    product = build_product(9, "Tie product", "6000")
    longer = build_priced_offer(product, "a-12m", EmiType.NO_COST, 12, "1000", "0")
    shorter_b = build_priced_offer(product, "b-6m", EmiType.NO_COST, 6, "1000", "0")
    shorter_a = build_priced_offer(product, "a-6m", EmiType.NO_COST, 6, "1000", "0")
    assert find_lowest_no_extra_cost_offer((longer, shorter_b, shorter_a)) == shorter_a


@pytest.mark.parametrize(
    ("highest_budget_in_rupees", "expected_ceiling_in_rupees"),
    [
        (None, None),
        ("2400", "2500"),
        ("2900", "3000"),
        ("3000", "3000"),
        ("3000.01", "3500"),
        ("4000", "4000"),
        ("4000.01", None),
    ],
)
def test_find_budget_ceiling_is_the_smallest_boundary_at_or_above_every_missed_budget(
    highest_budget_in_rupees: str | None, expected_ceiling_in_rupees: str | None
) -> None:
    """₹3,000 for the design week; none above the highest boundary."""
    highest_budget = (
        None if highest_budget_in_rupees is None else Money.from_rupees(highest_budget_in_rupees)
    )
    expected_ceiling = (
        None
        if expected_ceiling_in_rupees is None
        else Money.from_rupees(expected_ceiling_in_rupees)
    )
    assert find_budget_ceiling(highest_budget) == expected_ceiling


def test_cheapest_plan_under_the_ceiling_is_the_cardless_plan_for_the_128_gb_phone() -> None:
    """M5: "The only plan under ₹3,000 a month adds ₹2,600 extra in total"."""
    plan = find_cheapest_plan_under_ceiling(build_phone_128_gb_offers(), Money.from_rupees("3000"))
    assert plan is not None
    assert plan.quoted_monthly_installment == Money.from_rupees("2050")
    assert plan.schedule.extra_in_total == Money.from_rupees("2600")


def test_cheapest_plan_under_the_ceiling_prefers_less_extra_and_needs_a_ceiling() -> None:
    """At ₹4,000 plan A (₹0 extra) wins over C; no ceiling or no fitting plan gives none."""
    offers = build_phone_128_gb_offers()
    plan = find_cheapest_plan_under_ceiling(offers, Money.from_rupees("4000"))
    assert plan is not None
    assert plan.offer.offer_id == "no-cost-6m"
    assert find_cheapest_plan_under_ceiling(offers, None) is None
    assert find_cheapest_plan_under_ceiling(offers, Money.from_rupees("2000")) is None


def test_insight_product_has_the_most_missed_sales_then_the_higher_price_then_the_name() -> None:
    """Ties on count go to the dearer product, then to the name."""
    phone_128 = build_product_missed_sales(
        ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 3, "2000"
    )
    phone_64 = build_product_missed_sales(
        ProductOffers(PHONE_64_GB, build_phone_64_gb_offers()), 3, "2000"
    )
    same_price_later_name = build_product_missed_sales(
        ProductOffers(build_product(8, "Zeta phone", "22000"), build_phone_128_gb_offers()),
        3,
        "2000",
    )
    assert choose_insight_product([phone_64, same_price_later_name, phone_128]) == phone_128
    more_missed = build_product_missed_sales(
        ProductOffers(PHONE_64_GB, build_phone_64_gb_offers()), 4, "2000"
    )
    assert choose_insight_product([phone_128, more_missed]) == more_missed
    assert choose_insight_product([build_product_missed_sales(ProductOffers(EARBUDS, ()))]) is None


def test_design_analysis_has_12_missed_sales_on_the_128_gb_phone_under_3000() -> None:
    """The overall ceiling and the insight product's ceiling are both ₹3,000."""
    analysis = build_design_missed_sales_analysis()
    assert analysis.total_missed_count == 12
    assert analysis.budget_ceiling == Money.from_rupees("3000")
    assert analysis.insight is not None
    assert analysis.insight.product_offers.product == PHONE_128_GB
    assert analysis.insight.budget_ceiling == Money.from_rupees("3000")


def test_overall_ceiling_covers_every_products_missed_budgets() -> None:
    """Missed budgets up to ₹3,200 on another product lift the overall ceiling to ₹3,500."""
    analysis = MissedSalesAnalysis.from_products(
        [
            build_product_missed_sales(
                ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 12, "2900"
            ),
            build_product_missed_sales(
                ProductOffers(build_product(7, "Tablet", "30000"), build_phone_128_gb_offers()),
                5,
                "3200",
            ),
        ]
    )
    assert analysis.total_missed_count == 17
    assert analysis.budget_ceiling == Money.from_rupees("3500")


def test_missed_sales_report_of_the_design_week_describes_the_insight_product() -> None:
    """₹3,667 lowest no-cost monthly and the ₹2,050 plan that adds ₹2,600."""
    policy = SmallCountSuppressionPolicy()
    report = MissedSalesReport.from_analysis(
        build_design_missed_sales_analysis(),
        build_budget_bucket_report((5, 7, 14, 21, 49), None, (), policy),
        policy,
    )
    assert report.missed_count == ReportedCount(12, is_suppressed=False)
    assert report.budget_ceiling == Money.from_rupees("3000")
    assert report.product_insight is not None
    assert report.product_insight.product_name == "Example phone, 128 GB"
    assert report.product_insight.lowest_no_extra_cost_monthly == LOWEST_NO_COST_MONTHLY
    assert report.product_insight.cheapest_plan_under_ceiling is not None


def test_missed_sales_report_without_missed_sales_has_no_insight_and_shows_zero() -> None:
    """The empty shape: 0 missed, no ceiling, no insight product."""
    policy = SmallCountSuppressionPolicy()
    report = MissedSalesReport.from_analysis(
        MissedSalesAnalysis.from_products([]),
        build_budget_bucket_report((0, 0, 0, 0, 0), None, (), policy),
        policy,
    )
    assert report.missed_count == ReportedCount(0, is_suppressed=False)
    assert (report.budget_ceiling, report.product_insight) == (None, None)


def test_three_missed_sales_are_suppressed_in_the_report() -> None:
    """1 to 4 missed customers are "fewer than 5"."""
    policy = SmallCountSuppressionPolicy()
    analysis = MissedSalesAnalysis.from_products(
        [
            build_product_missed_sales(
                ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 3, "2900"
            )
        ]
    )
    report = MissedSalesReport.from_analysis(
        analysis, build_budget_bucket_report((0, 0, 0, 0, 0), None, (), policy), policy
    )
    assert report.missed_count == ReportedCount(None, is_suppressed=True)


def test_product_insight_needs_a_no_extra_cost_plan() -> None:
    """A tally on a product without such a plan (never produced by the query) gives none."""
    tally_without_plan = build_product_missed_sales(
        ProductOffers(EARBUDS, build_earbuds_offers()), 5, "300"
    )
    assert build_product_insight(tally_without_plan) is None
