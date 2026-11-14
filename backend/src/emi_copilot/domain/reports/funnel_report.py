"""FunnelReport: how many of a period's sales reached each stage, and where most were lost."""

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise

from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.reports.small_count_suppression import (
    ReportedCount,
    SmallCountSuppressionPolicy,
)

FUNNEL_STAGE_ORDER = (
    FunnelStage.STARTED,
    FunnelStage.BUDGET_TOLD,
    FunnelStage.PLANS_VIEWED,
    FunnelStage.AGREED,
    FunnelStage.PAID,
)
"""The stages in the order a sale moves through them, as M5's funnel lists them."""


@dataclass(frozen=True, slots=True)
class FunnelStageCount:
    """How many of the period's sales reached one stage, as the merchant may see it."""

    stage: FunnelStage
    count: ReportedCount


@dataclass(frozen=True, slots=True)
class FunnelDrop:
    """The largest fall between two adjacent stages; after_stage is the earlier one."""

    after_stage: FunnelStage
    count: ReportedCount


@dataclass(frozen=True, slots=True)
class FunnelDropSize:
    """A drop before suppression: the earlier stage and how many sales fell away after it."""

    after_stage: FunnelStage
    customer_count: int


def find_biggest_drop(counts_by_stage: Mapping[FunnelStage, int]) -> FunnelDropSize | None:
    """Gives the largest fall between adjacent stages; ties go to the earliest stage.

    A rise (possible while Layer 2 records an agreement without the customer steps) is no drop,
    so there is none when no stage falls, which includes the all-zero funnel.
    """
    biggest_drop: FunnelDropSize | None = None
    for earlier_stage, later_stage in pairwise(FUNNEL_STAGE_ORDER):
        fall = counts_by_stage.get(earlier_stage, 0) - counts_by_stage.get(later_stage, 0)
        if fall > 0 and (biggest_drop is None or fall > biggest_drop.customer_count):
            biggest_drop = FunnelDropSize(after_stage=earlier_stage, customer_count=fall)
    return biggest_drop


@dataclass(frozen=True, slots=True)
class FunnelReport:
    """A cohort funnel: the sales started in the period, counted by every stage each reached.

    Counts from 1 to 4, and a biggest drop of that size, are suppressed (plan Q3).
    """

    stages: tuple[FunnelStageCount, ...]
    biggest_drop: FunnelDrop | None

    @classmethod
    def from_stage_counts(
        cls, counts_by_stage: Mapping[FunnelStage, int], policy: SmallCountSuppressionPolicy
    ) -> "FunnelReport":
        """Builds the report from raw counts per stage; a stage missing from them counts zero."""
        drop_size = find_biggest_drop(counts_by_stage)
        return cls(
            stages=tuple(
                FunnelStageCount(stage, policy.report(counts_by_stage.get(stage, 0)))
                for stage in FUNNEL_STAGE_ORDER
            ),
            biggest_drop=(
                None
                if drop_size is None
                else FunnelDrop(drop_size.after_stage, policy.report(drop_size.customer_count))
            ),
        )

    def count_for(self, stage: FunnelStage) -> ReportedCount:
        """Gives the reported count of one stage."""
        return next(stage_count.count for stage_count in self.stages if stage_count.stage is stage)
