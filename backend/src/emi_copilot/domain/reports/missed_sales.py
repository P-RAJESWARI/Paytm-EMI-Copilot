"""Missed sales (plan Q12, refined): customers whose budget was under every no-extra-cost plan.

A missed sale is a sale started in the period that reached BUDGET_TOLD, never reached AGREED,
and whose budget is below the cheapest no-extra-cost monthly amount of its product. A product
with no no-extra-cost plan has no missed sales. Counting happens in one database query; the
rules for the threshold, the ceiling and the insight product live here.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.domain.reports.budget_buckets import BUDGET_BUCKET_BOUNDARIES, BudgetBucketReport
from emi_copilot.domain.reports.small_count_suppression import (
    ReportedCount,
    SmallCountSuppressionPolicy,
)


def find_lowest_no_extra_cost_offer(
    priced_offers: Sequence[PricedEmiOffer],
) -> PricedEmiOffer | None:
    """Gives the plan adding nothing to the price with the lowest quoted monthly figure.

    "Nothing extra" is our schedule's extra in total, as on the counter list; ties go to the
    shorter tenure, then the offer id, so the answer never depends on the gateway's order.
    """
    no_extra_cost_offers = [
        offer for offer in priced_offers if offer.schedule.extra_in_total.is_zero
    ]
    return min(
        no_extra_cost_offers,
        key=lambda offer: (
            offer.quoted_monthly_installment,
            offer.offer.tenure_in_months,
            offer.offer.offer_id,
        ),
        default=None,
    )


def is_missed_sale(
    monthly_budget: Money | None,
    has_agreed: bool,
    lowest_no_extra_cost_monthly: Money | None,
) -> bool:
    """Tells whether one sale is missed: a budget told, no agreement, budget under every plan.

    A budget equal to the lowest no-extra-cost monthly amount fits that plan, so it is not
    missed. The report query applies this same rule in SQL (ReportQueryRepository).
    """
    return (
        monthly_budget is not None
        and not has_agreed
        and lowest_no_extra_cost_monthly is not None
        and monthly_budget < lowest_no_extra_cost_monthly
    )


def find_budget_ceiling(
    highest_missed_budget: Money | None, boundaries: Sequence[Money] = BUDGET_BUCKET_BOUNDARIES
) -> Money | None:
    """Gives the smallest bucket boundary at or above every missed budget (₹3,000 in the demo).

    None when nothing was missed, or when a missed budget lies above the highest boundary.
    """
    if highest_missed_budget is None:
        return None
    return next((boundary for boundary in boundaries if boundary >= highest_missed_budget), None)


def find_cheapest_plan_under_ceiling(
    priced_offers: Sequence[PricedEmiOffer], budget_ceiling: Money | None
) -> PricedEmiOffer | None:
    """Gives the plan with a monthly figure at or below the ceiling that adds the least extra.

    Ties go to the lower monthly figure, then the offer id. None without a ceiling or a plan.
    """
    if budget_ceiling is None:
        return None
    return min(
        (offer for offer in priced_offers if offer.quoted_monthly_installment <= budget_ceiling),
        key=lambda offer: (
            offer.schedule.extra_in_total,
            offer.quoted_monthly_installment,
            offer.offer.offer_id,
        ),
        default=None,
    )


@dataclass(frozen=True, slots=True)
class MissedSalesTally:
    """One product's missed sales in a period, as the aggregate query counts them."""

    missed_count: int
    highest_missed_budget: Money | None


@dataclass(frozen=True, slots=True)
class ProductOffers:
    """One catalogue product with every plan the gateway quotes for it at its list price."""

    product: CatalogueProduct
    priced_offers: tuple[PricedEmiOffer, ...]

    @property
    def lowest_no_extra_cost_offer(self) -> PricedEmiOffer | None:
        """Gives the product's cheapest-monthly plan with nothing extra, if it has one."""
        return find_lowest_no_extra_cost_offer(self.priced_offers)


@dataclass(frozen=True, slots=True)
class ProductMissedSales:
    """A product with its missed-sales tally for one period."""

    product_offers: ProductOffers
    tally: MissedSalesTally

    @property
    def missed_count(self) -> int:
        """Gives how many of the product's sales were missed."""
        return self.tally.missed_count

    @property
    def budget_ceiling(self) -> Money | None:
        """Gives the smallest bucket boundary at or above every missed budget of the product."""
        return find_budget_ceiling(self.tally.highest_missed_budget)


def choose_insight_product(
    products_missed_sales: Sequence[ProductMissedSales],
) -> ProductMissedSales | None:
    """Gives the product with the most missed sales; ties: higher list price, then name.

    None when no product has a missed sale.
    """
    candidates = [product for product in products_missed_sales if product.missed_count > 0]
    return min(
        candidates,
        key=lambda candidate: (
            -candidate.missed_count,
            -candidate.product_offers.product.list_price.to_paise(),
            candidate.product_offers.product.name,
        ),
        default=None,
    )


@dataclass(frozen=True, slots=True)
class ProductInsight:
    """M5's missed-sales detail for the insight product, from quoted figures only."""

    product_id: str
    product_name: str
    lowest_no_extra_cost_monthly: Money
    cheapest_plan_under_ceiling: PricedEmiOffer | None


def build_product_insight(insight: ProductMissedSales) -> ProductInsight | None:
    """Describes the insight product; a product only has missed sales with a no-cost plan."""
    lowest_offer = insight.product_offers.lowest_no_extra_cost_offer
    if lowest_offer is None:
        return None
    return ProductInsight(
        product_id=insight.product_offers.product.id,
        product_name=insight.product_offers.product.name,
        lowest_no_extra_cost_monthly=lowest_offer.quoted_monthly_installment,
        cheapest_plan_under_ceiling=find_cheapest_plan_under_ceiling(
            insight.product_offers.priced_offers, insight.budget_ceiling
        ),
    )


@dataclass(frozen=True, slots=True)
class MissedSalesAnalysis:
    """Every product's missed sales in one period, the insight product and the overall ceiling."""

    products_missed_sales: tuple[ProductMissedSales, ...]
    insight: ProductMissedSales | None
    total_missed_count: int
    budget_ceiling: Money | None

    @classmethod
    def from_products(
        cls, products_missed_sales: Sequence[ProductMissedSales]
    ) -> "MissedSalesAnalysis":
        """Sums the products' missed sales; the overall ceiling covers every missed budget."""
        missed_budgets = [
            product.tally.highest_missed_budget
            for product in products_missed_sales
            if product.tally.highest_missed_budget is not None
        ]
        return cls(
            products_missed_sales=tuple(products_missed_sales),
            insight=choose_insight_product(products_missed_sales),
            total_missed_count=sum(product.missed_count for product in products_missed_sales),
            budget_ceiling=find_budget_ceiling(max(missed_budgets, default=None)),
        )


@dataclass(frozen=True, slots=True)
class MissedSalesReport:
    """M5's missed-sales card: the count, the ceiling, the insight product and the buckets."""

    missed_count: ReportedCount
    budget_ceiling: Money | None
    product_insight: ProductInsight | None
    budget_buckets: BudgetBucketReport

    @classmethod
    def from_analysis(
        cls,
        analysis: MissedSalesAnalysis,
        budget_buckets: BudgetBucketReport,
        policy: SmallCountSuppressionPolicy,
    ) -> "MissedSalesReport":
        """Builds the card; a missed count from 1 to 4 is suppressed like every other count."""
        return cls(
            missed_count=policy.report(analysis.total_missed_count),
            budget_ceiling=analysis.budget_ceiling,
            product_insight=(
                None if analysis.insight is None else build_product_insight(analysis.insight)
            ),
            budget_buckets=budget_buckets,
        )
