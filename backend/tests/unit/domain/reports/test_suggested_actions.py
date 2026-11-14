"""Suggested-action strategies: each fires on its own condition with computed paise figures."""

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.reports.missed_sales import MissedSalesAnalysis, ProductOffers
from emi_copilot.domain.reports.small_count_suppression import (
    ReportedCount,
    SmallCountSuppressionPolicy,
)
from emi_copilot.domain.reports.suggested_actions import (
    CheaperModelAction,
    CheaperModelSuggestion,
    LongerNoCostPlanAction,
    LongerNoCostPlanSuggestion,
    SuggestedActionCode,
    SuggestedNoCostTenure,
    SuggestionContext,
    suggest_actions,
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

POLICY = SmallCountSuppressionPolicy()


def _context(analysis: MissedSalesAnalysis) -> SuggestionContext:
    """Wraps an analysis with the default policy."""
    return SuggestionContext(analysis=analysis, policy=POLICY)


def test_design_week_suggests_9_and_12_month_no_cost_then_the_64_gb_phone() -> None:
    """The two M5 tips, in strategy order, with the NoCostStrategy installments on ₹22,000."""
    actions = suggest_actions(_context(build_design_missed_sales_analysis()))
    assert actions == (
        LongerNoCostPlanAction(
            product_id=PHONE_128_GB.id,
            product_name="Example phone, 128 GB",
            current_no_cost_tenure_in_months=6,
            current_no_cost_monthly=Money.from_rupees("3666.67"),
            suggested_tenures=(
                SuggestedNoCostTenure(9, Money.from_rupees("2444.44")),
                SuggestedNoCostTenure(12, Money.from_rupees("1833.33")),
            ),
            missed_count=ReportedCount(12, is_suppressed=False),
            budget_ceiling=Money.from_rupees("3000"),
        ),
        CheaperModelAction(
            product_id=PHONE_64_GB.id,
            product_name="Example phone, 64 GB",
            list_price=Money.from_rupees("18000"),
            monthly_installment=Money.from_rupees("3000"),
            tenure_in_months=6,
        ),
    )
    assert [action.action_code for action in actions] == [
        SuggestedActionCode.ASK_BRAND_FOR_LONGER_NO_COST_PLAN,
        SuggestedActionCode.KEEP_CHEAPER_MODEL_READY,
    ]


def test_no_missed_sales_suggests_nothing() -> None:
    """Neither strategy fires without an insight product."""
    analysis = MissedSalesAnalysis.from_products(
        [build_product_missed_sales(ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()))]
    )
    assert suggest_actions(_context(analysis)) == ()


def test_longer_no_cost_plan_reports_a_small_missed_count_as_suppressed() -> None:
    """Three missed sales still suggest the plan, without telling the merchant "3"."""
    analysis = MissedSalesAnalysis.from_products(
        [
            build_product_missed_sales(
                ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 3, "2900"
            )
        ]
    )
    (action,) = LongerNoCostPlanSuggestion().suggest(_context(analysis))
    assert isinstance(action, LongerNoCostPlanAction)
    assert action.missed_count == ReportedCount(None, is_suppressed=True)


def test_longer_no_cost_plan_skips_tenures_not_longer_than_the_current_one() -> None:
    """A 12-month no-cost plan exists: only longer tenures would help, and none is listed."""
    offer = build_priced_offer(PHONE_128_GB, "no-cost-12m", EmiType.NO_COST, 12, "1833.33", "0")
    analysis = MissedSalesAnalysis.from_products(
        [build_product_missed_sales(ProductOffers(PHONE_128_GB, (offer,)), 6, "1500")]
    )
    assert LongerNoCostPlanSuggestion().suggest(_context(analysis)) == ()
    nine_month_offer = build_priced_offer(
        PHONE_128_GB, "no-cost-9m", EmiType.NO_COST, 9, "2444.44", "0"
    )
    analysis = MissedSalesAnalysis.from_products(
        [build_product_missed_sales(ProductOffers(PHONE_128_GB, (nine_month_offer,)), 6, "2000")]
    )
    (action,) = LongerNoCostPlanSuggestion().suggest(_context(analysis))
    assert isinstance(action, LongerNoCostPlanAction)
    assert [tenure.tenure_in_months for tenure in action.suggested_tenures] == [12]


def test_longer_no_cost_plan_skips_tenures_that_cannot_be_split_into_installments() -> None:
    """Seven paise over 9 or 12 months has no whole-paise schedule, so nothing is suggested."""
    tiny_product = build_product(6, "Tiny item", "0.07")
    offer = build_priced_offer(tiny_product, "no-cost-1m", EmiType.NO_COST, 1, "0.07", "0")
    analysis = MissedSalesAnalysis.from_products(
        [build_product_missed_sales(ProductOffers(tiny_product, (offer,)), 5, "0.01")]
    )
    assert LongerNoCostPlanSuggestion().suggest(_context(analysis)) == ()


def test_longer_no_cost_plan_needs_the_insight_to_have_a_no_cost_plan() -> None:
    """A tally on a product without one never comes from the query; nothing is suggested."""
    analysis = MissedSalesAnalysis.from_products(
        [build_product_missed_sales(ProductOffers(EARBUDS, build_earbuds_offers()), 5, "300")]
    )
    assert LongerNoCostPlanSuggestion().suggest(_context(analysis)) == ()


def test_cheaper_model_needs_a_ceiling() -> None:
    """Missed budgets above every boundary give no ceiling, so no model can be said to fit."""
    analysis = MissedSalesAnalysis.from_products(
        [
            build_product_missed_sales(
                ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 6, "4200"
            ),
            build_product_missed_sales(ProductOffers(PHONE_64_GB, build_phone_64_gb_offers())),
        ]
    )
    assert CheaperModelSuggestion().suggest(_context(analysis)) == ()


def test_cheaper_model_does_not_fire_when_its_no_cost_monthly_is_above_the_ceiling() -> None:
    """Budgets under ₹2,500: the 64 GB phone's ₹3,000 does not fit."""
    analysis = MissedSalesAnalysis.from_products(
        [
            build_product_missed_sales(
                ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 6, "2400"
            ),
            build_product_missed_sales(ProductOffers(PHONE_64_GB, build_phone_64_gb_offers())),
            build_product_missed_sales(ProductOffers(EARBUDS, build_earbuds_offers())),
        ]
    )
    assert CheaperModelSuggestion().suggest(_context(analysis)) == ()


def test_cheaper_model_picks_the_dearest_fitting_model_and_ignores_dearer_ones() -> None:
    """Of two cheaper models that fit, the one closer in price; a dearer model never counts."""
    cheaper_fitting = build_product(4, "Example phone, 32 GB", "12000")
    dearer_fitting = build_product(5, "Example tablet", "30000")
    analysis = MissedSalesAnalysis.from_products(
        [
            build_product_missed_sales(
                ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 12, "2900"
            ),
            build_product_missed_sales(
                ProductOffers(
                    cheaper_fitting,
                    (build_priced_offer(cheaper_fitting, "nc", EmiType.NO_COST, 6, "2000", "0"),),
                )
            ),
            build_product_missed_sales(ProductOffers(PHONE_64_GB, build_phone_64_gb_offers())),
            build_product_missed_sales(
                ProductOffers(
                    dearer_fitting,
                    (build_priced_offer(dearer_fitting, "nc", EmiType.NO_COST, 12, "2500", "0"),),
                )
            ),
        ]
    )
    (action,) = CheaperModelSuggestion().suggest(_context(analysis))
    assert isinstance(action, CheaperModelAction)
    assert action.product_id == PHONE_64_GB.id


def test_cheaper_model_tie_on_price_goes_to_the_name() -> None:
    """Two fitting models at one price: the name decides, so the order is stable."""
    alpha = build_product(10, "Alpha phone", "18000")
    analysis = MissedSalesAnalysis.from_products(
        [
            build_product_missed_sales(
                ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 12, "2900"
            ),
            build_product_missed_sales(ProductOffers(PHONE_64_GB, build_phone_64_gb_offers())),
            build_product_missed_sales(ProductOffers(alpha, build_phone_64_gb_offers())),
        ]
    )
    (action,) = CheaperModelSuggestion().suggest(_context(analysis))
    assert isinstance(action, CheaperModelAction)
    assert action.product_name == "Alpha phone"
