"""The agreed plan's installments are rebuilt from its frozen figures exactly as they were shown."""

import pytest

from emi_copilot.domain.consent import ConsentPlanSnapshot
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.customer.consent_types import rebuild_agreed_schedule


def build_design_snapshot(
    plan_kind: EmiType, tenure_in_months: int, monthly_in_paise: int, extra_in_paise: int
) -> ConsentPlanSnapshot:
    """Freezes one design plan on the ₹22,000 phone."""
    return ConsentPlanSnapshot(
        product_id="01JCPRODUCT00000000000001",
        product_name="Example phone, 128 GB",
        price=Money.from_rupees(22000),
        chosen_plan=ChosenPlan(
            offer_id=f"offer-{tenure_in_months}",
            plan_kind=plan_kind,
            lender_label="Demo lender",
            tenure_in_months=tenure_in_months,
            monthly_installment=Money.from_paise(monthly_in_paise),
            extra_in_total=Money.from_paise(extra_in_paise),
            total_payable=Money.from_paise(2_200_000 + extra_in_paise),
        ),
    )


@pytest.mark.parametrize(
    ("snapshot", "expected_regular_in_paise", "expected_last_in_paise"),
    [
        (build_design_snapshot(EmiType.NO_COST, 6, 366_667, 0), 366_667, 366_665),
        (build_design_snapshot(EmiType.STANDARD, 6, 385_000, 110_000), 385_000, 385_000),
        (build_design_snapshot(EmiType.STANDARD, 12, 205_000, 260_000), 205_000, 205_000),
    ],
    ids=["plan-a-no-cost", "plan-b-card", "plan-c-cardless"],
)
def test_rebuild_agreed_schedule_gives_the_design_installments_summing_to_the_total(
    snapshot: ConsentPlanSnapshot, expected_regular_in_paise: int, expected_last_in_paise: int
) -> None:
    """Plan A is 366,667 x 5 then 366,665; B and C are even; every schedule sums to the total."""
    schedule = rebuild_agreed_schedule(snapshot)
    assert schedule.regular_installment.to_paise() == expected_regular_in_paise
    assert schedule.last_installment.to_paise() == expected_last_in_paise
    assert schedule.total_payable == snapshot.chosen_plan.total_payable
    assert schedule.extra_in_total == snapshot.chosen_plan.extra_in_total
