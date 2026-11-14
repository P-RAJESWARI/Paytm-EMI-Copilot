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


def report_stage_counts(
    counts_by_stage: Mapping[FunnelStage, int], policy: SmallCountSuppressionPolicy
) -> tuple[FunnelStageCount, ...]:
    """Reports every stage in order; a zero right after a suppressed stage is suppressed too.

    The cascade carries on: a zero after that suppressed zero is suppressed as well, so no 0
    ever stands beside "fewer than 5" and shows where those few customers stopped.
    """
    stage_counts: list[FunnelStageCount] = []
    previous_count = policy.report(0)
    for stage in FUNNEL_STAGE_ORDER:
        reported_count = policy.report_after(counts_by_stage.get(stage, 0), previous_count)
        stage_counts.append(FunnelStageCount(stage, reported_count))
        previous_count = reported_count
    return tuple(stage_counts)


def report_drop(
    drop_size: FunnelDropSize,
    stages: tuple[FunnelStageCount, ...],
    policy: SmallCountSuppressionPolicy,
) -> FunnelDrop | None:
    """Reports the biggest drop: None beside a suppressed stage; a count of 1 to 4 is suppressed.

    Beside a suppressed stage even the stage name is withheld: its count could be subtracted to
    recover the hidden one (20 started, a drop of 17, so 3 told a budget), and its name alone
    tells where a few customers stopped (1 started, told a budget and saw the plans: "after
    seeing the plans" points at that one person), which rule 6 forbids. Between two shown stages
    a drop of 1 to 4 keeps its stage, which the merchant sees anyway, and hides its count.
    """
    later_stage = FUNNEL_STAGE_ORDER[FUNNEL_STAGE_ORDER.index(drop_size.after_stage) + 1]
    is_a_neighbour_suppressed = any(
        stage_count.count.is_suppressed
        for stage_count in stages
        if stage_count.stage in (drop_size.after_stage, later_stage)
    )
    if is_a_neighbour_suppressed:
        return None
    return FunnelDrop(drop_size.after_stage, policy.report(drop_size.customer_count))


@dataclass(frozen=True, slots=True)
class FunnelReport:
    """A cohort funnel: the sales started in the period, counted by every stage each reached.

    Counts from 1 to 4, a zero right after a suppressed stage, and a biggest drop of 1 to 4 are
    suppressed (plan Q3); a biggest drop beside a suppressed stage is omitted (None), stage and
    all. The cohort holds no sale still CHOOSING (ReportQueryRepository).
    """

    stages: tuple[FunnelStageCount, ...]
    biggest_drop: FunnelDrop | None

    @classmethod
    def from_stage_counts(
        cls, counts_by_stage: Mapping[FunnelStage, int], policy: SmallCountSuppressionPolicy
    ) -> "FunnelReport":
        """Builds the report from raw counts per stage; a stage missing from them counts zero."""
        stages = report_stage_counts(counts_by_stage, policy)
        drop_size = find_biggest_drop(counts_by_stage)
        return cls(
            stages=stages,
            biggest_drop=None if drop_size is None else report_drop(drop_size, stages, policy),
        )

    def count_for(self, stage: FunnelStage) -> ReportedCount:
        """Gives the reported count of one stage."""
        return next(stage_count.count for stage_count in self.stages if stage_count.stage is stage)
