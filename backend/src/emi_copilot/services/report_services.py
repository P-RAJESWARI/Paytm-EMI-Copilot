"""The M5 report services: funnel, missed sales, suggested actions and money due, per shop.

Each reads only the signed-in shop's data (scoped by its merchant id or shop code) and returns
domain reports whose counts already went through SmallCountSuppressionPolicy (plan Q3).
"""

from dataclasses import dataclass

from emi_copilot.adapters.settlement.port import SettlementPort
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.domain.reports.budget_buckets import build_budget_bucket_report
from emi_copilot.domain.reports.funnel_report import FunnelReport
from emi_copilot.domain.reports.missed_sales import MissedSalesReport
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.reports.reporting_period import ReportingPeriod, ReportingRange
from emi_copilot.domain.reports.small_count_suppression import SmallCountSuppressionPolicy
from emi_copilot.domain.reports.suggested_actions import (
    SuggestedAction,
    SuggestionContext,
    suggest_actions,
)
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.missed_sales_analyser import MissedSalesAnalyser
from emi_copilot.services.report_periods import ReportPeriods


@dataclass(frozen=True, slots=True)
class FunnelReportView:
    """The funnel of one range, with the period it covers."""

    reporting_range: ReportingRange
    period: ReportingPeriod
    report: FunnelReport


@dataclass(frozen=True, slots=True)
class MissedSalesReportView:
    """The missed-sales card of one range, with the period it covers."""

    reporting_range: ReportingRange
    period: ReportingPeriod
    report: MissedSalesReport


class FunnelReportService:
    """Counts the shop's cohort funnel for a range or for an explicit period."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        report_periods: ReportPeriods,
        policy: SmallCountSuppressionPolicy,
    ) -> None:
        """Keeps the unit-of-work factory, the period calculator and the count policy."""
        self._unit_of_work_factory = unit_of_work_factory
        self._report_periods = report_periods
        self._policy = policy

    def get_funnel_report(
        self, principal: MerchantPrincipal, reporting_range: ReportingRange
    ) -> FunnelReportView:
        """Gives the funnel of the sales started in today's, this week's or this month's period."""
        period = self._report_periods.containing_now(reporting_range)
        return FunnelReportView(reporting_range, period, self.build_report(principal, period))

    def build_report(self, principal: MerchantPrincipal, period: ReportingPeriod) -> FunnelReport:
        """Gives the funnel of the shop's sales started in the period."""
        with self._unit_of_work_factory() as unit_of_work:
            counts = unit_of_work.report_queries.count_sales_reaching_each_stage(
                principal.merchant_id, period.starts_at, period.ends_at
            )
        return FunnelReport.from_stage_counts(counts, self._policy)


class MissedSalesReportService:
    """Builds M5's missed-sales card and its budget buckets for a range or period."""

    def __init__(
        self,
        missed_sales_analyser: MissedSalesAnalyser,
        report_periods: ReportPeriods,
        policy: SmallCountSuppressionPolicy,
    ) -> None:
        """Keeps the analyser, the period calculator and the count policy."""
        self._missed_sales_analyser = missed_sales_analyser
        self._report_periods = report_periods
        self._policy = policy

    def get_missed_sales_report(
        self, principal: MerchantPrincipal, reporting_range: ReportingRange
    ) -> MissedSalesReportView:
        """Gives the card for today's, this week's or this month's period."""
        period = self._report_periods.containing_now(reporting_range)
        return MissedSalesReportView(reporting_range, period, self.build_report(principal, period))

    def build_report(
        self, principal: MerchantPrincipal, period: ReportingPeriod
    ) -> MissedSalesReport:
        """Gives the card of the shop's sales started in the period."""
        findings = self._missed_sales_analyser.analyse(principal, period)
        insight = findings.analysis.insight
        budget_buckets = build_budget_bucket_report(
            findings.budget_counts,
            findings.analysis.budget_ceiling,
            () if insight is None else insight.product_offers.priced_offers,
            self._policy,
            cohort_sale_count=findings.cohort_sale_count,
        )
        return MissedSalesReport.from_analysis(findings.analysis, budget_buckets, self._policy)


class SuggestedActionsService:
    """Gives the deterministic suggestions of M5's "What you can do to sell more"."""

    def __init__(
        self,
        missed_sales_analyser: MissedSalesAnalyser,
        report_periods: ReportPeriods,
        policy: SmallCountSuppressionPolicy,
    ) -> None:
        """Keeps the analyser, the period calculator and the count policy."""
        self._missed_sales_analyser = missed_sales_analyser
        self._report_periods = report_periods
        self._policy = policy

    def get_suggested_actions(
        self, principal: MerchantPrincipal, reporting_range: ReportingRange
    ) -> tuple[SuggestedAction, ...]:
        """Gives the actions for today's, this week's or this month's period, in stable order."""
        return self.build_actions(principal, self._report_periods.containing_now(reporting_range))

    def build_actions(
        self, principal: MerchantPrincipal, period: ReportingPeriod
    ) -> tuple[SuggestedAction, ...]:
        """Gives the actions for the shop's sales started in the period."""
        findings = self._missed_sales_analyser.analyse(principal, period)
        return suggest_actions(SuggestionContext(findings.analysis, self._policy))


class MoneyDueReportService:
    """Gives what brands still owe the shop, through the (Mock) settlement port (plan Q13)."""

    def __init__(self, settlement: SettlementPort) -> None:
        """Keeps the settlement port."""
        self._settlement = settlement

    def get_money_due(self, principal: MerchantPrincipal) -> MoneyDueReport:
        """Gives the shop's expected batches, their total and the next date; not range-filtered."""
        return MoneyDueReport.from_batches(
            self._settlement.find_expected_brand_settlements(principal.shop_code)
        )
