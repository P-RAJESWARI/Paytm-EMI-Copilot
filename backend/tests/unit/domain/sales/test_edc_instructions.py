"""Tests for EdcInstructions: the card machine steps M4 shows for an agreed plan."""

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales import (
    EDC_EMI_PROGRAMME_BY_PLAN_KIND,
    EdcEmiProgramme,
    EdcInstructions,
)
from tests.sale_builders import build_no_cost_chosen_plan, build_standard_chosen_plan


def test_no_cost_plan_is_keyed_as_brand_emi_with_nothing_extra() -> None:
    """Design plan A: Brand EMI, 6 months, the ₹22,000 price, no extra."""
    assert EdcInstructions.for_chosen_plan(
        build_no_cost_chosen_plan(), "Example phone, 128 GB"
    ) == EdcInstructions(
        emi_programme=EdcEmiProgramme.BRAND_EMI,
        product_name="Example phone, 128 GB",
        tenure_in_months=6,
        is_no_extra_cost=True,
        amount=Money.from_rupees("22000"),
    )


def test_standard_plan_is_keyed_as_bank_emi_on_the_price_not_the_total() -> None:
    """Design plan B: the machine takes the ₹22,000 price; the bank adds the ₹1,100 itself."""
    instructions = EdcInstructions.for_chosen_plan(build_standard_chosen_plan(), "Phone")
    assert instructions.emi_programme is EdcEmiProgramme.BANK_EMI
    assert instructions.is_no_extra_cost is False
    assert instructions.amount == Money.from_rupees("22000")


def test_every_plan_kind_has_an_edc_programme() -> None:
    """A new plan kind cannot reach the counter without a decision."""
    assert set(EDC_EMI_PROGRAMME_BY_PLAN_KIND) == set(EmiType)
