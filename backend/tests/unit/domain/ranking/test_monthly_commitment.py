"""Tests for calculate_monthly_commitment: the largest single installment (ADR 0020 decision 3)."""

from emi_copilot.domain.money import Money
from emi_copilot.domain.ranking import calculate_monthly_commitment
from tests.plan_builders import (
    build_card_plan_b,
    build_cardless_plan_c,
    build_no_cost_plan_a,
    build_priced_plan,
)


def test_calculate_monthly_commitment_design_plans_equal_the_shown_monthly_amount() -> None:
    """A ₹3,666.67 (last ₹3,666.65 is smaller), B ₹3,850.00 and C ₹2,050.00."""
    assert calculate_monthly_commitment(build_no_cost_plan_a()) == Money.from_rupees("3666.67")
    assert calculate_monthly_commitment(build_card_plan_b()) == Money.from_rupees("3850.00")
    assert calculate_monthly_commitment(build_cardless_plan_c()) == Money.from_rupees("2050.00")


def test_calculate_monthly_commitment_larger_last_installment_is_used() -> None:
    """₹10.00 over 3 months is 3.33, 3.33 then 3.34, so the commitment is ₹3.34."""
    priced_plan = build_priced_plan("offer-small", 3, Money.from_paise(0), Money.from_rupees("10"))
    assert priced_plan.schedule.last_installment == Money.from_rupees("3.34")
    assert calculate_monthly_commitment(priced_plan) == Money.from_rupees("3.34")


def test_calculate_monthly_commitment_larger_lender_quote_is_used() -> None:
    """A lender quoting ₹3,851.00 for plan B is judged on ₹3,851.00, not our ₹3,850.00."""
    priced_plan = build_priced_plan(
        "offer-plan-b",
        6,
        Money.from_rupees("1100"),
        Money.from_rupees("22000"),
        quoted_monthly_installment=Money.from_rupees("3851.00"),
    )
    assert calculate_monthly_commitment(priced_plan) == Money.from_rupees("3851.00")
