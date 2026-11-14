"""Budget buckets: how many customers told a monthly budget in each range (M5's bar chart)."""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from emi_copilot.domain.errors import InvalidReportDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType, PricedEmiOffer
from emi_copilot.domain.reports.small_count_suppression import (
    ReportedCount,
    SmallCountSuppressionPolicy,
)

BUDGET_BUCKET_BOUNDARIES = (
    Money.from_rupees("2500"),
    Money.from_rupees("3000"),
    Money.from_rupees("3500"),
    Money.from_rupees("4000"),
)
"""The four boundaries of M5's five buckets; each bucket includes its lower bound."""


@dataclass(frozen=True, slots=True)
class BudgetRange:
    """A half-open monthly range: lower_bound <= amount < upper_bound; no upper bound is open."""

    lower_bound: Money
    upper_bound: Money | None

    def contains(self, monthly_amount: Money) -> bool:
        """Tells whether a monthly amount falls in this range."""
        return monthly_amount >= self.lower_bound and (
            self.upper_bound is None or monthly_amount < self.upper_bound
        )


def build_budget_ranges(
    boundaries: Sequence[Money] = BUDGET_BUCKET_BOUNDARIES,
) -> tuple[BudgetRange, ...]:
    """Gives [0, b1), [b1, b2), ... [bn, open) for strictly increasing boundaries."""
    if any(lower >= upper for lower, upper in pairwise(boundaries)):
        raise InvalidReportDataError("Budget bucket boundaries must be strictly increasing.")
    lower_bounds = (Money.from_paise(0), *boundaries)
    upper_bounds: tuple[Money | None, ...] = (*boundaries, None)
    return tuple(
        BudgetRange(lower_bound, upper_bound)
        for lower_bound, upper_bound in zip(lower_bounds, upper_bounds, strict=True)
    )


BUDGET_RANGES = build_budget_ranges()
"""Under ₹2,500; ₹2,500 to 3,000; ₹3,000 to 3,500; ₹3,500 to 4,000; ₹4,000 and above."""


@dataclass(frozen=True, slots=True)
class BucketPlan:
    """One quoted plan of the insight product, placed in the bucket its monthly figure falls in."""

    plan_kind: EmiType
    lender_label: str
    monthly_installment: Money


@dataclass(frozen=True, slots=True)
class BudgetBucket:
    """One budget range: its customer count, whether it lies under the ceiling, and its plans."""

    budget_range: BudgetRange
    count: ReportedCount
    is_under_ceiling: bool
    plans: tuple[BucketPlan, ...]


@dataclass(frozen=True, slots=True)
class BudgetBucketReport:
    """Every bucket, or none at all when fewer than 5 customers told a budget (plan Q3).

    The threshold is the suppression policy's, so buckets and counts hide at the same size.
    """

    total_count: ReportedCount
    are_buckets_hidden: bool
    buckets: tuple[BudgetBucket, ...]


def _is_under_ceiling(budget_range: BudgetRange, budget_ceiling: Money | None) -> bool:
    """Tells whether the whole range lies at or below the missed-sales ceiling."""
    return (
        budget_ceiling is not None
        and budget_range.upper_bound is not None
        and budget_range.upper_bound <= budget_ceiling
    )


def _plans_in_range(
    budget_range: BudgetRange, insight_offers: Sequence[PricedEmiOffer]
) -> tuple[BucketPlan, ...]:
    """Lists the insight product's quoted plans whose monthly figure falls in the range."""
    return tuple(
        BucketPlan(
            plan_kind=offer.offer.emi_type,
            lender_label=offer.offer.lender_label,
            monthly_installment=offer.quoted_monthly_installment,
        )
        for offer in sorted(
            insight_offers,
            key=lambda priced_offer: (
                priced_offer.quoted_monthly_installment,
                priced_offer.offer.offer_id,
            ),
        )
        if budget_range.contains(offer.quoted_monthly_installment)
    )


def build_budget_bucket_report(
    customer_counts: Sequence[int],
    budget_ceiling: Money | None,
    insight_offers: Sequence[PricedEmiOffer],
    policy: SmallCountSuppressionPolicy,
) -> BudgetBucketReport:
    """Builds the buckets from one raw count per BUDGET_RANGES entry, in the same order.

    The plans are the insight product's quoted figures (never recomputed), cheapest monthly
    first; with no insight product, no bucket lists a plan.
    """
    if len(customer_counts) != len(BUDGET_RANGES):
        raise InvalidReportDataError("Give exactly one customer count per budget range.")
    total_customer_count = sum(customer_counts)
    total_count = policy.report(total_customer_count)
    if total_customer_count < policy.minimum_shown_count:
        return BudgetBucketReport(total_count=total_count, are_buckets_hidden=True, buckets=())
    return BudgetBucketReport(
        total_count=total_count,
        are_buckets_hidden=False,
        buckets=tuple(
            BudgetBucket(
                budget_range=budget_range,
                count=policy.report(customer_count),
                is_under_ceiling=_is_under_ceiling(budget_range, budget_ceiling),
                plans=_plans_in_range(budget_range, insight_offers),
            )
            for budget_range, customer_count in zip(BUDGET_RANGES, customer_counts, strict=True)
        ),
    )
