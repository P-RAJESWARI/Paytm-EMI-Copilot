"""AllowedNumbers: built only from engine and report figures; suppressed counts never allowed."""

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.core.indian_rupee_formatter import (
    format_paise_as_whole_rupees,
    group_digits_the_indian_way,
)
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.number_audit import AllowedNumbers, NumberAuditService
from emi_copilot.domain.number_audit.allowed_numbers import whole_rupees_of
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.reports.small_count_suppression import ReportedCount
from emi_copilot.domain.reports.suggested_actions import (
    LongerNoCostPlanAction,
    SuggestedNoCostTenure,
)
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageTemplate
from emi_copilot.domain.reports.weekly_message_wording import MessageLanguage
from tests.report_builders import DESIGN_FUNNEL_COUNTS, build_design_weekly_message_facts
from tests.sale_builders import build_no_cost_chosen_plan, build_standard_chosen_plan

WEEKLY_TEMPLATE = WeeklyMessageTemplate(format_paise_as_whole_rupees)


@given(amount_in_paise=st.integers(min_value=0, max_value=10**15))
def test_whole_rupees_of_matches_the_backend_rupee_formatter(amount_in_paise: int) -> None:
    """The audit rounds exactly like the text formatter (half-up), without importing core."""
    whole_rupees = whole_rupees_of(Money.from_paise(amount_in_paise))
    assert format_paise_as_whole_rupees(amount_in_paise) == "₹" + group_digits_the_indian_way(
        whole_rupees
    )


def test_allowed_numbers_for_design_plan_a_are_its_shown_figures_and_label_digits() -> None:
    """Plan A shows ₹3,667 (from ₹3,666.67), ₹0, ₹22,000 twice and 6 months."""
    allowed = AllowedNumbers.for_plan_explanation(
        build_no_cost_chosen_plan(), label_texts=("Brand", "Example phone, 128 GB")
    )
    assert allowed == AllowedNumbers(
        rupee_amounts=frozenset({3667, 0, 22_000}), plain_numbers=frozenset({6, 128})
    )


def test_allowed_numbers_for_design_plan_b_include_the_extra_and_the_total() -> None:
    """Plan B: ₹3,850 a month, ₹1,100 extra, ₹23,100 in total on a ₹22,000 price."""
    allowed = AllowedNumbers.for_plan_explanation(build_standard_chosen_plan(), label_texts=())
    assert allowed.rupee_amounts == frozenset({3850, 1100, 23_100, 22_000})
    assert allowed.plain_numbers == frozenset({6})


def test_allowed_numbers_for_the_design_week_hold_every_figure_the_template_may_say() -> None:
    """Counts, money due, batches, dates, tenures and product digits of the design week."""
    allowed = AllowedNumbers.for_weekly_message(build_design_weekly_message_facts())
    assert allowed.rupee_amounts == frozenset(
        {184_000, 72_000, 64_000, 48_000, 3000, 3667, 2444, 1833, 18_000}
    )
    assert allowed.plain_numbers == frozenset(
        {120, 96, 88, 51, 44, 37, 12, 9, 15, 13, 28, 2026, 2027, 6, 128, 64}
    )


@pytest.mark.parametrize("small_count", [1, 2, 3, 4])
def test_allowed_numbers_for_weekly_message_never_allow_a_suppressed_count(
    small_count: int,
) -> None:
    """Rule 6: a count from 1 to 4 is "fewer than 5" and never an allowed number."""
    facts = build_design_weekly_message_facts(
        {**DESIGN_FUNNEL_COUNTS, FunnelStage.PAID: small_count}, phone_missed_count=small_count
    )
    allowed = AllowedNumbers.for_weekly_message(facts)
    assert small_count not in allowed.plain_numbers
    assert 3000 not in allowed.rupee_amounts
    assert 2444 not in allowed.rupee_amounts


def test_number_audit_weekly_message_with_a_suppressed_count_fails() -> None:
    """3 paid is suppressed, so "3 of 120" is an unexpected number."""
    facts = build_design_weekly_message_facts({**DESIGN_FUNNEL_COUNTS, FunnelStage.PAID: 3})
    result = NumberAuditService().audit(
        "3 of 120 customers bought on EMI.", AllowedNumbers.for_weekly_message(facts), ()
    )
    assert result.has_passed is False
    assert result.mismatched_tokens == ("3",)


def test_number_audit_weekly_message_with_a_batch_date_passes() -> None:
    """Day and year numbers of the brand batches may be said: "13 Jan 2027"."""
    allowed = AllowedNumbers.for_weekly_message(build_design_weekly_message_facts())
    text = "₹1,84,000 is due from brands, with a payment around 13 Jan 2027."
    assert NumberAuditService().audit(text, allowed, (184_000,)).has_passed is True


def test_number_audit_weekly_template_tamil_text_passes() -> None:
    """The Tamil weekly template holds only allowed figures and no forbidden word."""
    facts = build_design_weekly_message_facts()
    message = WEEKLY_TEMPLATE.render_in(MessageLanguage.TAMIL, facts)
    text = " ".join((message.title, *message.paragraphs))
    assert NumberAuditService().audit(text, AllowedNumbers.for_weekly_message(facts), ()).has_passed


def test_number_audit_weekly_template_english_text_fails_only_on_one_and_first() -> None:
    """The template's "One thing to do" and "first payment" are words the audit cannot allow.

    "one" is the plain number 1, which is never allowed beside suppressed counts, and "first" is
    an ordinal. The template is the fallback and is not audited; AI text must avoid both words.
    """
    facts = build_design_weekly_message_facts()
    message = WEEKLY_TEMPLATE.render_in(MessageLanguage.ENGLISH, facts)
    text = " ".join((message.title, *message.paragraphs))
    result = NumberAuditService().audit(text, AllowedNumbers.for_weekly_message(facts), ())
    assert result.mismatched_tokens == ("first", "One")


def test_allowed_numbers_for_an_empty_week_hold_only_zero_and_the_period_dates() -> None:
    """No sales, no batches, no actions: only zero counts and the week's own dates."""
    facts = replace(
        build_design_weekly_message_facts(dict.fromkeys(DESIGN_FUNNEL_COUNTS, 0), 0),
        money_due=MoneyDueReport.from_batches(()),
        suggested_actions=(),
    )
    allowed = AllowedNumbers.for_weekly_message(facts)
    assert allowed.plain_numbers == frozenset({0, 9, 15, 2026})
    assert allowed.rupee_amounts == frozenset({0, 3000})


def test_allowed_numbers_for_a_longer_no_cost_action_without_a_ceiling_skip_the_ceiling() -> None:
    """An action without a budget ceiling adds only its monthly figures and tenures."""
    action = LongerNoCostPlanAction(
        product_id="product-1",
        product_name="Example tablet 10",
        current_no_cost_tenure_in_months=6,
        current_no_cost_monthly=Money.from_rupees("5000"),
        suggested_tenures=(SuggestedNoCostTenure(15, Money.from_rupees("2000")),),
        missed_count=ReportedCount(customer_count=12, is_suppressed=False),
        budget_ceiling=None,
    )
    facts = replace(
        build_design_weekly_message_facts(),
        money_due=MoneyDueReport.from_batches(()),
        suggested_actions=(action,),
    )
    allowed = AllowedNumbers.for_weekly_message(facts)
    assert {5000, 2000} <= allowed.rupee_amounts
    assert {6, 15, 10} <= allowed.plain_numbers
