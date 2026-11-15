"""Prompt facts: camelCase JSON in field order, read back only when exactly well formed."""

import json

import pytest

from emi_copilot.adapters.ai.prompt_facts import (
    ExplanationPromptFacts,
    facts_to_json,
    to_camel_case,
)

PLAN_A_FACTS = ExplanationPromptFacts(
    plan_kind="NO_COST",
    plan_display_name="கட்டணமில்லா EMI",
    lender_label="Brand",
    tenure_in_months=6,
    monthly_amount_in_rupees=3667,
    extra_in_total_in_rupees=0,
    total_payable_in_rupees=22_000,
    price_in_rupees=22_000,
    funder_note=None,
)


def test_facts_to_json_writes_camel_case_keys_and_readable_tamil() -> None:
    """The wire convention is camelCase; Tamil is not escaped, so prompts stay readable."""
    facts_json = facts_to_json(PLAN_A_FACTS)
    assert '"planDisplayName": "கட்டணமில்லா EMI"' in facts_json
    assert list(json.loads(facts_json))[:2] == ["planKind", "planDisplayName"]


def test_explanation_facts_read_back_from_their_own_json() -> None:
    """The Mock recognises explanation facts by reading them back."""
    facts_object = json.loads(facts_to_json(PLAN_A_FACTS))
    assert ExplanationPromptFacts.from_json_object(facts_object) == PLAN_A_FACTS


@pytest.mark.parametrize(
    "change",
    [
        {"extraKey": 1},
        {"tenureInMonths": "6"},
        {"tenureInMonths": True},
        {"planKind": None},
        {"monthlyAmountInRupees": 3667.0},
    ],
)
def test_explanation_facts_with_other_keys_or_types_are_not_read(change: dict[str, object]) -> None:
    """Anything but exactly these well-typed fields is not treated as explanation facts."""
    facts_object = {**json.loads(facts_to_json(PLAN_A_FACTS)), **change}
    assert ExplanationPromptFacts.from_json_object(facts_object) is None


@pytest.mark.parametrize(
    ("field_name", "expected_key"),
    [("tenure_in_months", "tenureInMonths"), ("plan_kind", "planKind"), ("n", "n")],
)
def test_to_camel_case_turns_snake_case_into_wire_keys(field_name: str, expected_key: str) -> None:
    """snake_case in Python, camelCase on the wire."""
    assert to_camel_case(field_name) == expected_key
