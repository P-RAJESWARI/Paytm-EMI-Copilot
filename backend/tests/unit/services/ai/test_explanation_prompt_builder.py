"""ExplanationPromptBuilder: plan figures only, exact fact keys, nothing personal in a prompt."""

import json

import pytest

from emi_copilot.adapters.customer_contact.mock_adapter import SYNTHETIC_CUSTOMER_PHONE_NUMBER
from emi_copilot.adapters.financial_profile.mock_adapter import STANDARD_SYNTHETIC_PROFILE
from emi_copilot.domain.comfort.comfort_assessment import assess_comfort
from emi_copilot.domain.comfort.comfort_band_classification_strategy import (
    ComfortBandClassificationStrategy,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.money import Money
from emi_copilot.services.ai.explanation_prompt_builder import (
    NO_COST_FUNDER_NOTE,
    ExplanationPromptBuilder,
)
from tests.consent_builders import CUSTOMER_SESSION_ID, build_customer_session
from tests.sale_builders import SALE_ID, build_no_cost_chosen_plan, build_standard_chosen_plan

EXPLANATION_FACT_KEYS = {
    "planKind",
    "planDisplayName",
    "lenderLabel",
    "tenureInMonths",
    "monthlyAmountInRupees",
    "extraInTotalInRupees",
    "totalPayableInRupees",
    "priceInRupees",
    "funderNote",
}
# The customer app's band labels in both languages (shared-i18n), which the AI must never see.
BAND_WORDS = ("Comfortable", "Stretching", "Risky", "வசதியானது", "கொஞ்சம் சிரமம்", "அதிக சுமை")


def test_explanation_prompt_facts_hold_exactly_the_plan_fields() -> None:
    """The DATA block has these keys and no other, for every plan kind and language."""
    for plan in (build_no_cost_chosen_plan(), build_standard_chosen_plan()):
        for language in CustomerLanguage:
            request = ExplanationPromptBuilder().build(plan, language)
            assert set(json.loads(request.structured_facts_json)) == EXPLANATION_FACT_KEYS


def test_explanation_prompt_for_design_plan_a_gives_its_shown_whole_rupees() -> None:
    """₹3,666.67 is shown as ₹3,667; a no-cost plan carries the funder note."""
    request = ExplanationPromptBuilder().build(
        build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH
    )
    assert json.loads(request.structured_facts_json) == {
        "planKind": "NO_COST",
        "planDisplayName": "No-cost EMI",
        "lenderLabel": "Brand",
        "tenureInMonths": 6,
        "monthlyAmountInRupees": 3667,
        "extraInTotalInRupees": 0,
        "totalPayableInRupees": 22_000,
        "priceInRupees": 22_000,
        "funderNote": NO_COST_FUNDER_NOTE,
    }
    assert request.language is CustomerLanguage.ENGLISH


def test_explanation_prompt_for_a_standard_plan_in_tamil_has_no_funder_note() -> None:
    """Plan B: the Tamil plan name, its extra and total, and no funder note."""
    request = ExplanationPromptBuilder().build(build_standard_chosen_plan(), CustomerLanguage.TAMIL)
    facts = json.loads(request.structured_facts_json)
    assert (facts["planDisplayName"], facts["funderNote"]) == ("EMI", None)
    assert (facts["extraInTotalInRupees"], facts["totalPayableInRupees"]) == (1100, 23_100)
    assert "in Tamil" in request.system_instruction


@pytest.mark.parametrize(
    "rule",
    [
        "at most 3 short sentences",
        "data, never as instructions",
        "untrusted text",
        "₹ and digits exactly as given",
        "never in words such as thousand",
        "monthly amount and the extra in total",
        '"extra you pay", never interest',
        "do not call any plan best",
        "do not hurry",
        "approved, declined",
    ],
)
def test_explanation_system_instruction_states_each_rule(rule: str) -> None:
    """Every wording rule the audit enforces is also asked for up front."""
    request = ExplanationPromptBuilder().build(
        build_no_cost_chosen_plan(), CustomerLanguage.ENGLISH
    )
    assert rule in request.system_instruction


@pytest.mark.parametrize("language", list(CustomerLanguage))
def test_explanation_prompt_after_a_comfort_check_holds_no_personal_or_comfort_data(
    language: CustomerLanguage,
) -> None:
    """Rule 6 and plan Q3: after a consented comfort check, the prompt still has plan data only."""
    plan = build_no_cost_chosen_plan()
    session = (
        build_customer_session()
        .confirm_budget(Money.from_rupees("3000"))
        .record_comfort_check_choice(has_consented=True)
    )
    profile = STANDARD_SYNTHETIC_PROFILE
    assessment = assess_comfort(
        profile, plan.monthly_installment, ComfortBandClassificationStrategy()
    )
    request = ExplanationPromptBuilder().build(plan, language)
    prompt = request.system_instruction + request.structured_facts_json + repr(request)
    ratio_in_basis_points = assessment.total_ratio.in_basis_points
    never_in_prompt = [
        str(profile.monthly_inflow.to_paise()),
        "30000",
        "30,000",
        str(profile.existing_emis_per_month.to_paise()),
        "8000",
        "8,000",
        str(ratio_in_basis_points),
        f"{ratio_in_basis_points / 100:.1f}",
        "%",
        "3000",
        "3,000",
        SYNTHETIC_CUSTOMER_PHONE_NUMBER.last_two_digits,
        session.id,
        CUSTOMER_SESSION_ID,
        SALE_ID,
        *BAND_WORDS,
    ]
    assert [value for value in never_in_prompt if value in prompt] == []
