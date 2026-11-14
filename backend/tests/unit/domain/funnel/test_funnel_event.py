"""FunnelEvent: one sale reached one stage; a budget amount exists only on BUDGET_TOLD."""

import pytest

from emi_copilot.domain.errors import InvalidSaleDataError
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from tests.sale_builders import SALE_STARTED_AT, build_funnel_event


def test_funnel_stage_matches_the_five_report_steps_in_order() -> None:
    """Started, told a budget, saw the plans, agreed to a plan, paid (M5)."""
    assert [stage.value for stage in FunnelStage] == [
        "STARTED",
        "BUDGET_TOLD",
        "PLANS_VIEWED",
        "AGREED",
        "PAID",
    ]


def test_budget_told_event_carries_the_monthly_budget() -> None:
    """The confirmed monthly amount is kept for the aggregate budget buckets only."""
    budget_event = build_funnel_event(
        stage=FunnelStage.BUDGET_TOLD, monthly_budget=Money.from_rupees("3000")
    )
    assert budget_event.monthly_budget == Money.from_rupees("3000")


@pytest.mark.parametrize(
    ("stage", "monthly_budget"),
    [
        (FunnelStage.BUDGET_TOLD, None),
        (FunnelStage.STARTED, Money.from_rupees("3000")),
        (FunnelStage.BUDGET_TOLD, Money.from_paise(0)),
        (FunnelStage.BUDGET_TOLD, Money.from_rupees("0.001")),
    ],
)
def test_budget_on_the_wrong_stage_or_not_positive_raises(
    stage: FunnelStage, monthly_budget: Money | None
) -> None:
    """A budget is a positive whole-paise amount, recorded exactly on BUDGET_TOLD."""
    with pytest.raises(InvalidSaleDataError):
        build_funnel_event(stage=stage, monthly_budget=monthly_budget)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("id", ""),
        ("sale_id", " "),
        ("merchant_id", ""),
        ("stage", "STARTED"),
        ("occurred_at", SALE_STARTED_AT.replace(tzinfo=None)),
    ],
)
def test_funnel_event_with_an_invalid_field_raises(field_name: str, value: object) -> None:
    """Ids are non-blank, the stage is a FunnelStage and the moment has a time zone."""
    with pytest.raises(InvalidSaleDataError):
        build_funnel_event(**{field_name: value})
