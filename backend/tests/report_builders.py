"""Builders of report inputs on the design sample data (DESIGN_SPEC section 4), synthetic ids."""

from dataclasses import replace
from datetime import date
from zoneinfo import ZoneInfo

from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiOffer, EmiType, PricedEmiOffer, price_emi_offer
from emi_copilot.domain.reports.budget_buckets import build_budget_bucket_report
from emi_copilot.domain.reports.funnel_report import FunnelReport
from emi_copilot.domain.reports.missed_sales import (
    MissedSalesAnalysis,
    MissedSalesReport,
    MissedSalesTally,
    ProductMissedSales,
    ProductOffers,
)
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.reports.reporting_period import ReportingPeriod
from emi_copilot.domain.reports.small_count_suppression import SmallCountSuppressionPolicy
from emi_copilot.domain.reports.suggested_actions import SuggestionContext, suggest_actions
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageFacts
from emi_copilot.domain.settlements import BrandSettlementBatch, BrandSettlementStatus

REPORT_MERCHANT_ID = "01JCREPORTMERCHANT00000001"


def build_product(product_number: int, name: str, list_price_in_rupees: str) -> CatalogueProduct:
    """A product of the report merchant with synthetic gateway ids."""
    return CatalogueProduct(
        id=f"01JCREPORTPRODUCT{product_number:09d}",
        merchant_id=REPORT_MERCHANT_ID,
        name=name,
        list_price=Money.from_rupees(list_price_in_rupees),
        gateway_product_id=f"gateway-product-{product_number}",
        gateway_brand_id="gateway-brand",
        gateway_category_id="gateway-category",
    )


PHONE_128_GB = build_product(1, "Example phone, 128 GB", "22000")
PHONE_64_GB = build_product(2, "Example phone, 64 GB", "18000")
EARBUDS = build_product(3, "Example earbuds", "2499")


def build_priced_offer(  # noqa: PLR0913, PLR0917 - one parameter per quoted figure
    product: CatalogueProduct,
    offer_id: str,
    emi_type: EmiType,
    tenure_in_months: int,
    monthly_in_rupees: str,
    extra_in_rupees: str,
    lender_label: str = "Brand",
) -> PricedEmiOffer:
    """Quotes one plan on the product's list price and prices it with our engine."""
    offer = EmiOffer(
        offer_id=offer_id,
        lender_label=lender_label,
        emi_type=emi_type,
        tenure_in_months=tenure_in_months,
        quoted_monthly_installment=Money.from_rupees(monthly_in_rupees),
        quoted_extra_in_total=Money.from_rupees(extra_in_rupees),
    )
    return price_emi_offer(offer, product.list_price)


def build_phone_128_gb_offers() -> tuple[PricedEmiOffer, ...]:
    """Design plans A, B and C on ₹22,000."""
    return (
        build_priced_offer(PHONE_128_GB, "no-cost-6m", EmiType.NO_COST, 6, "3666.67", "0"),
        build_priced_offer(
            PHONE_128_GB, "card-6m", EmiType.STANDARD, 6, "3850", "1100", "Your card's bank"
        ),
        build_priced_offer(
            PHONE_128_GB, "cardless-12m", EmiType.STANDARD, 12, "2050", "2600", "Cardless lender"
        ),
    )


def build_phone_64_gb_offers() -> tuple[PricedEmiOffer, ...]:
    """The 64 GB phone at ₹18,000: no-cost 6 x ₹3,000 and card 6 x ₹3,150."""
    return (
        build_priced_offer(PHONE_64_GB, "no-cost-6m", EmiType.NO_COST, 6, "3000", "0"),
        build_priced_offer(
            PHONE_64_GB, "card-6m", EmiType.STANDARD, 6, "3150", "900", "Your card's bank"
        ),
    )


def build_earbuds_offers() -> tuple[PricedEmiOffer, ...]:
    """The earbuds at ₹2,499: one card plan, nothing without extra cost."""
    return (
        build_priced_offer(
            EARBUDS, "card-6m", EmiType.STANDARD, 6, "437.33", "124.95", "Your card's bank"
        ),
    )


def build_product_missed_sales(
    product_offers: ProductOffers,
    missed_count: int = 0,
    highest_budget_in_rupees: str | None = None,
) -> ProductMissedSales:
    """A product with a tally of missed sales and the highest missed budget."""
    highest_budget = (
        None if highest_budget_in_rupees is None else Money.from_rupees(highest_budget_in_rupees)
    )
    return ProductMissedSales(product_offers, MissedSalesTally(missed_count, highest_budget))


def build_design_missed_sales_analysis() -> MissedSalesAnalysis:
    """The design week: 12 missed sales on the 128 GB phone, budgets up to ₹2,900."""
    return MissedSalesAnalysis.from_products(
        [
            build_product_missed_sales(
                ProductOffers(PHONE_128_GB, build_phone_128_gb_offers()), 12, "2900"
            ),
            build_product_missed_sales(ProductOffers(PHONE_64_GB, build_phone_64_gb_offers())),
            build_product_missed_sales(ProductOffers(EARBUDS, build_earbuds_offers())),
        ]
    )


def build_design_settlement_batches() -> tuple[BrandSettlementBatch, ...]:
    """DESIGN_SPEC section 4: ₹1,84,000 in three batches, listed out of order on purpose."""
    return (
        BrandSettlementBatch(
            3, 10, Money.from_rupees("48000"), date(2027, 2, 12), BrandSettlementStatus.NOT_YET_DUE
        ),
        BrandSettlementBatch(
            1, 18, Money.from_rupees("72000"), date(2027, 1, 13), BrandSettlementStatus.CLAIM_FILED
        ),
        BrandSettlementBatch(
            2,
            16,
            Money.from_rupees("64000"),
            date(2027, 1, 28),
            BrandSettlementStatus.WAITING_FOR_BRAND,
        ),
    )


DESIGN_FUNNEL_COUNTS = {
    FunnelStage.STARTED: 120,
    FunnelStage.BUDGET_TOLD: 96,
    FunnelStage.PLANS_VIEWED: 88,
    FunnelStage.AGREED: 51,
    FunnelStage.PAID: 44,
}
"""DESIGN_SPEC section 4's seven-day funnel."""


def build_design_weekly_message_facts(
    funnel_counts: dict[FunnelStage, int] | None = None, phone_missed_count: int = 12
) -> WeeklyMessageFacts:
    """The design week of 9 to 15 November 2026; counts can be changed to test suppression."""
    policy = SmallCountSuppressionPolicy()
    phone_128_gb, *other_products = build_design_missed_sales_analysis().products_missed_sales
    analysis = MissedSalesAnalysis.from_products(
        [
            replace(
                phone_128_gb, tally=replace(phone_128_gb.tally, missed_count=phone_missed_count)
            ),
            *other_products,
        ]
    )
    empty_buckets = build_budget_bucket_report(
        (0, 0, 0, 0, 0), None, (), policy, cohort_sale_count=0
    )
    return WeeklyMessageFacts(
        period=ReportingPeriod.week_starting(date(2026, 11, 9), ZoneInfo("Asia/Kolkata")),
        funnel=FunnelReport.from_stage_counts(funnel_counts or DESIGN_FUNNEL_COUNTS, policy),
        missed_sales=MissedSalesReport.from_analysis(analysis, empty_buckets, policy),
        money_due=MoneyDueReport.from_batches(build_design_settlement_batches()),
        suggested_actions=suggest_actions(SuggestionContext(analysis, policy)),
    )
