"""MissedSalesAnalyser: one period's missed sales and budget counts, for three report services."""

from dataclasses import dataclass

from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.domain.reports.budget_buckets import BUDGET_BUCKET_BOUNDARIES
from emi_copilot.domain.reports.missed_sales import (
    MissedSalesAnalysis,
    MissedSalesTally,
    ProductMissedSales,
    ProductOffers,
)
from emi_copilot.domain.reports.reporting_period import ReportingPeriod
from emi_copilot.domain.reports.small_count_suppression import SmallCountSuppressionPolicy
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService

_NO_MISSED_SALES = MissedSalesTally(missed_count=0, highest_missed_budget=None)


@dataclass(frozen=True, slots=True)
class MissedSalesFindings:
    """The period's missed-sales analysis beside its raw budget count per range."""

    analysis: MissedSalesAnalysis
    budget_counts: tuple[int, ...]


class MissedSalesAnalyser:
    """Reads the shop's products, quotes each through offer discovery, then counts in SQL.

    The products are read and the transaction closed before any gateway call; the counts run
    in a second, read-only transaction. Every plan figure is the gateway's quote with our
    schedule (OfferDiscoveryService), never recomputed. A gateway error fails the report. Sales
    still CHOOSING are not counted, and every figure derived from a suppressed missed count is
    dropped here (MissedSalesAnalysis.without_suppressed_details), so the card, the suggestions
    and the weekly message all read the same suppressed analysis.
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        offer_discovery_service: OfferDiscoveryService,
        policy: SmallCountSuppressionPolicy,
    ) -> None:
        """Keeps the unit-of-work factory, offer discovery and the count policy."""
        self._unit_of_work_factory = unit_of_work_factory
        self._offer_discovery_service = offer_discovery_service
        self._policy = policy

    def analyse(self, principal: MerchantPrincipal, period: ReportingPeriod) -> MissedSalesFindings:
        """Gives the shop's missed sales per product and its budget counts for the period."""
        merchant_id = principal.merchant_id
        with self._unit_of_work_factory() as unit_of_work:
            products = unit_of_work.products.list_for_merchant(merchant_id)
        products_offers = [
            ProductOffers(
                product,
                self._offer_discovery_service.discover_offers(product.to_offer_discovery_query()),
            )
            for product in products
        ]
        thresholds_by_product_id = {
            product_offers.product.id: lowest_offer.quoted_monthly_installment
            for product_offers in products_offers
            if (lowest_offer := product_offers.lowest_no_extra_cost_offer) is not None
        }
        with self._unit_of_work_factory() as unit_of_work:
            tallies = unit_of_work.report_queries.tally_missed_sales(
                merchant_id, period.starts_at, period.ends_at, thresholds_by_product_id
            )
            budget_counts = unit_of_work.report_queries.count_budgets_per_range(
                merchant_id, period.starts_at, period.ends_at, BUDGET_BUCKET_BOUNDARIES
            )
        analysis = MissedSalesAnalysis.from_products(
            [
                ProductMissedSales(
                    product_offers, tallies.get(product_offers.product.id, _NO_MISSED_SALES)
                )
                for product_offers in products_offers
            ]
        ).without_suppressed_details(self._policy)
        return MissedSalesFindings(analysis=analysis, budget_counts=budget_counts)
