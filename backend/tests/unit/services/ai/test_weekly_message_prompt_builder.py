"""WeeklyMessagePromptBuilder: report figures only; suppressed counts never reach a prompt."""

import json
from dataclasses import replace

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.number_audit import AllowedNumbers, NumberTokenExtractor
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageFacts
from emi_copilot.domain.reports.weekly_message_wording import MessageLanguage
from emi_copilot.services.ai.weekly_message_prompt_builder import WeeklyMessagePromptBuilder
from tests.report_builders import DESIGN_FUNNEL_COUNTS, build_design_weekly_message_facts

WEEKLY_FACT_KEYS = {
    "periodFirstDay",
    "periodLastDay",
    "customersStarted",
    "customersPaid",
    "biggestDropAfterStage",
    "missedSalesCount",
    "missedSalesMonthlyCeilingInRupees",
    "moneyDueFromBrandsInRupees",
    "nextBrandPaymentDay",
    "brandBatches",
    "suggestedAction",
}


def build_facts_object(facts: WeeklyMessageFacts) -> dict[str, object]:
    """Builds the English request and gives its DATA block as a JSON object."""
    request = WeeklyMessagePromptBuilder().build(facts, MessageLanguage.ENGLISH)
    facts_object: dict[str, object] = json.loads(request.structured_facts_json)
    return facts_object


def list_numbers_in(value: object) -> list[int]:
    """Lists every number in a JSON value: whole numbers, and digits inside texts."""
    if isinstance(value, dict):
        return [number for item in value.values() for number in list_numbers_in(item)]
    if isinstance(value, list):
        return [number for item in value for number in list_numbers_in(item)]
    if isinstance(value, str):
        return [
            token.value
            for token in NumberTokenExtractor().extract(value)
            if token.value is not None
        ]
    return [value] if isinstance(value, int) else []


def test_weekly_prompt_for_the_design_week_holds_exactly_the_report_fields() -> None:
    """The design week: counts, money due, batches by date and the first action."""
    facts_object = build_facts_object(build_design_weekly_message_facts())
    assert set(facts_object) == WEEKLY_FACT_KEYS
    assert facts_object["periodFirstDay"] == "9 November 2026"
    assert (facts_object["customersStarted"], facts_object["customersPaid"]) == (120, 44)
    assert facts_object["biggestDropAfterStage"] == "PLANS_VIEWED"
    assert facts_object["missedSalesMonthlyCeilingInRupees"] == 3000
    assert facts_object["moneyDueFromBrandsInRupees"] == 184_000
    assert facts_object["nextBrandPaymentDay"] == "13 January 2027"
    assert facts_object["brandBatches"] == [
        {"amountInRupees": 72_000, "expectedDay": "13 January 2027"},
        {"amountInRupees": 64_000, "expectedDay": "28 January 2027"},
        {"amountInRupees": 48_000, "expectedDay": "12 February 2027"},
    ]
    assert facts_object["suggestedAction"] == {
        "actionCode": "ASK_BRAND_FOR_LONGER_NO_COST_PLAN",
        "productName": "Example phone, 128 GB",
        "tenuresInMonths": [9, 12],
        "monthlyAmountsInRupees": [2444, 1833],
        "listPriceInRupees": None,
    }


def test_weekly_prompt_numbers_are_all_allowed_by_the_weekly_audit() -> None:
    """Whatever the AI copies from the facts passes AllowedNumbers.for_weekly_message."""
    facts = build_design_weekly_message_facts()
    allowed = AllowedNumbers.for_weekly_message(facts)
    numbers = list_numbers_in(build_facts_object(facts))
    assert numbers
    assert set(numbers) <= allowed.plain_numbers | allowed.rupee_amounts


def test_weekly_prompt_with_suppressed_counts_sends_null_and_no_action() -> None:
    """3 paid and 3 missed are "fewer than 5": null, with no ceiling, drop or action."""
    facts = build_design_weekly_message_facts(
        {**DESIGN_FUNNEL_COUNTS, FunnelStage.PAID: 3}, phone_missed_count=3
    )
    facts_object = build_facts_object(facts)
    assert facts_object["customersPaid"] is None
    assert facts_object["missedSalesCount"] is None
    assert facts_object["missedSalesMonthlyCeilingInRupees"] is None
    assert facts_object["biggestDropAfterStage"] is None
    assert facts_object["suggestedAction"] is None
    assert 3 not in list_numbers_in(facts_object)


def test_weekly_prompt_with_a_cheaper_model_action_and_no_batches() -> None:
    """A cheaper-model action carries its list price; no batches means no payment day."""
    design_facts = build_design_weekly_message_facts()
    facts = replace(
        design_facts,
        money_due=MoneyDueReport.from_batches(()),
        suggested_actions=design_facts.suggested_actions[1:],
    )
    facts_object = build_facts_object(facts)
    assert facts_object["nextBrandPaymentDay"] is None
    assert facts_object["brandBatches"] == []
    assert facts_object["suggestedAction"] == {
        "actionCode": "KEEP_CHEAPER_MODEL_READY",
        "productName": "Example phone, 64 GB",
        "tenuresInMonths": [6],
        "monthlyAmountsInRupees": [3000],
        "listPriceInRupees": 18_000,
    }


def test_weekly_prompt_in_tamil_names_the_language_and_asks_for_digits_only() -> None:
    """The instruction names Tamil and forbids number words and ordinals (step 4.2 finding)."""
    request = WeeklyMessagePromptBuilder().build(
        build_design_weekly_message_facts(), MessageLanguage.TAMIL
    )
    assert request.language is CustomerLanguage.TAMIL
    assert "in Tamil" in request.system_instruction
    assert "never use number words or ordinals such as one, first" in request.system_instruction
    assert "null count was hidden for privacy" in request.system_instruction
