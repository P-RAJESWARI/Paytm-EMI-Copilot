"""Wire schemas of the funnel and missed-sales reports: aggregates only (rule 6).

A count from 1 to 4 is sent as customerCount null with isSuppressed true (plan Q3). Budget
names appear only in the missed-sales schemas, as counts per range and a range boundary;
no customer's own budget, step or progress is ever here.
"""

from datetime import date
from typing import Annotated

from pydantic import Field

from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.reports.budget_buckets import BucketPlan, BudgetBucket
from emi_copilot.domain.reports.missed_sales import ProductInsight
from emi_copilot.domain.reports.reporting_period import ReportingRange
from emi_copilot.dtos.wire_types import (
    CamelCaseQueryModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    PositiveAmountInPaise,
)
from emi_copilot.services.report_services import FunnelReportView, MissedSalesReportView

CustomerCount = Annotated[int | None, Field(ge=0, description="Null when suppressed (1 to 4).")]


def to_paise_or_none(amount: Money | None) -> int | None:
    """Gives an optional amount as integer paise."""
    return None if amount is None else amount.to_paise()


class ReportRangeQuery(CamelCaseQueryModel):
    """Which span of the shop's calendar (IST) the report covers."""

    reporting_range: Annotated[
        ReportingRange,
        Field(
            alias="range",
            description="TODAY, THIS_WEEK (Monday to Sunday) or THIS_MONTH, in IST.",
        ),
    ]


class FunnelStageCountResponse(CamelCaseResponseModel):
    """How many of the period's sales reached one stage."""

    stage: FunnelStage
    customer_count: CustomerCount
    is_suppressed: bool


class FunnelDropResponse(CamelCaseResponseModel):
    """The largest fall between adjacent stages; afterStage is the earlier stage."""

    after_stage: FunnelStage
    customer_count: CustomerCount
    is_suppressed: bool


class FunnelReportResponse(CamelCaseResponseModel):
    """M5 "Where customers drop off": the period's started sales that are no longer CHOOSING."""

    reporting_range: Annotated[ReportingRange, Field(alias="range")]
    period_start_date: date
    period_end_date: date
    stages: list[FunnelStageCountResponse]
    biggest_drop: FunnelDropResponse | None

    @classmethod
    def from_view(cls, view: FunnelReportView) -> "FunnelReportResponse":
        """Builds the wire report from the service view."""
        drop = view.report.biggest_drop
        return cls(
            reporting_range=view.reporting_range,
            period_start_date=view.period.period_start_date,
            period_end_date=view.period.period_end_date,
            stages=[
                FunnelStageCountResponse(
                    stage=stage_count.stage,
                    customer_count=stage_count.count.customer_count,
                    is_suppressed=stage_count.count.is_suppressed,
                )
                for stage_count in view.report.stages
            ],
            biggest_drop=(
                None
                if drop is None
                else FunnelDropResponse(
                    after_stage=drop.after_stage,
                    customer_count=drop.count.customer_count,
                    is_suppressed=drop.count.is_suppressed,
                )
            ),
        )


class BucketPlanResponse(CamelCaseResponseModel):
    """One quoted plan of the insight product whose monthly figure falls in the range."""

    plan_kind: EmiType
    lender_label: str
    monthly_installment_in_paise: PositiveAmountInPaise

    @classmethod
    def from_plan(cls, plan: BucketPlan) -> "BucketPlanResponse":
        """Builds the wire plan."""
        return cls(
            plan_kind=plan.plan_kind,
            lender_label=plan.lender_label,
            monthly_installment_in_paise=plan.monthly_installment.to_paise(),
        )


class BudgetBucketResponse(CamelCaseResponseModel):
    """How many customers told a monthly amount in [lowerBound, upperBound); null upper is open."""

    lower_bound_in_paise: NonNegativeAmountInPaise
    upper_bound_in_paise: PositiveAmountInPaise | None
    customer_count: CustomerCount
    is_suppressed: bool
    is_under_ceiling: bool
    plans: list[BucketPlanResponse]

    @classmethod
    def from_bucket(cls, bucket: BudgetBucket) -> "BudgetBucketResponse":
        """Builds the wire bucket."""
        return cls(
            lower_bound_in_paise=bucket.budget_range.lower_bound.to_paise(),
            upper_bound_in_paise=to_paise_or_none(bucket.budget_range.upper_bound),
            customer_count=bucket.count.customer_count,
            is_suppressed=bucket.count.is_suppressed,
            is_under_ceiling=bucket.is_under_ceiling,
            plans=[BucketPlanResponse.from_plan(plan) for plan in bucket.plans],
        )


class CheapestPlanUnderCeilingResponse(CamelCaseResponseModel):
    """The insight product's plan at or under the ceiling that adds the least extra."""

    monthly_installment_in_paise: PositiveAmountInPaise
    extra_in_total_in_paise: NonNegativeAmountInPaise


class ProductInsightResponse(CamelCaseResponseModel):
    """The product most missed sales were for, with its quoted figures."""

    product_id: str
    product_name: str
    lowest_no_extra_cost_monthly_in_paise: PositiveAmountInPaise
    cheapest_plan_under_ceiling: CheapestPlanUnderCeilingResponse | None

    @classmethod
    def from_insight(cls, insight: ProductInsight) -> "ProductInsightResponse":
        """Builds the wire insight from the quoted plan figures."""
        cheapest = insight.cheapest_plan_under_ceiling
        return cls(
            product_id=insight.product_id,
            product_name=insight.product_name,
            lowest_no_extra_cost_monthly_in_paise=insight.lowest_no_extra_cost_monthly.to_paise(),
            cheapest_plan_under_ceiling=(
                None
                if cheapest is None
                else CheapestPlanUnderCeilingResponse(
                    monthly_installment_in_paise=cheapest.quoted_monthly_installment.to_paise(),
                    extra_in_total_in_paise=cheapest.schedule.extra_in_total.to_paise(),
                )
            ),
        )


class MissedSalesReportResponse(CamelCaseResponseModel):
    """M5 "Missed sales": who wanted less than every no-extra-cost plan, and the buckets."""

    reporting_range: Annotated[ReportingRange, Field(alias="range")]
    period_start_date: date
    period_end_date: date
    missed_customer_count: CustomerCount
    is_suppressed: bool
    budget_ceiling_in_paise: PositiveAmountInPaise | None
    product_insight: ProductInsightResponse | None
    budget_total_customer_count: CustomerCount
    are_budget_buckets_hidden: bool
    budget_buckets: list[BudgetBucketResponse]

    @classmethod
    def from_view(cls, view: MissedSalesReportView) -> "MissedSalesReportResponse":
        """Builds the wire card from the service view."""
        report = view.report
        buckets = report.budget_buckets
        return cls(
            reporting_range=view.reporting_range,
            period_start_date=view.period.period_start_date,
            period_end_date=view.period.period_end_date,
            missed_customer_count=report.missed_count.customer_count,
            is_suppressed=report.missed_count.is_suppressed,
            budget_ceiling_in_paise=to_paise_or_none(report.budget_ceiling),
            product_insight=(
                None
                if report.product_insight is None
                else ProductInsightResponse.from_insight(report.product_insight)
            ),
            budget_total_customer_count=buckets.total_count.customer_count,
            are_budget_buckets_hidden=buckets.are_buckets_hidden,
            budget_buckets=[BudgetBucketResponse.from_bucket(bucket) for bucket in buckets.buckets],
        )
