"""NumberAuditService: AI text passes only with engine figures, required amounts, plain words."""

import re

from hypothesis import assume, given
from hypothesis import strategies as st

from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.money import Money
from emi_copilot.domain.number_audit import (
    AllowedNumbers,
    NumberAuditFailureReason,
    NumberAuditService,
)
from emi_copilot.domain.number_audit.allowed_numbers import whole_rupees_of
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.customer.template_explanation_service import TemplateExplanationService
from tests.sale_builders import build_no_cost_chosen_plan, build_standard_chosen_plan

DESIGN_PLAN_A_TEXT = (
    "No-cost EMI: you pay ₹3,667 each month for 6 months. The extra you pay in total is ₹0."
)
PLAN_A_REQUIRED_AMOUNTS = (3667, 0)
# Written as an escape because it looks like the letter o.
TAMIL_DIGIT_ZERO = "\u0be6"
RUPEE_AMOUNT_PATTERN = re.compile(r"₹[0-9]+(?:,[0-9]+)*")


def design_plan_a() -> ChosenPlan:
    """Design plan A on ₹22,000: no-cost, 6 x ₹3,666.67 shown as ₹3,667, ₹0 extra (ADR 0001)."""
    return build_no_cost_chosen_plan()


def audit_plan_a_text(text: str) -> tuple[bool, tuple[str, ...]]:
    """Audits a text against design plan A and gives whether it passed and its mismatches."""
    result = NumberAuditService().audit(
        text,
        AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=()),
        required_rupee_amounts=PLAN_A_REQUIRED_AMOUNTS,
    )
    return result.has_passed, result.mismatched_tokens


def test_number_audit_explanation_with_one_wrong_digit_fails() -> None:
    """The checkpoint case: ₹3,676 instead of ₹3,667 is caught and quoted as written."""
    plan = design_plan_a()  # no-cost, 6 x ₹3,667, ₹0 extra, ₹22,000
    result = NumberAuditService().audit(
        "No-cost EMI: you pay ₹3,676 each month for 6 months. The extra you pay in total is ₹0.",
        AllowedNumbers.for_plan_explanation(plan, label_texts=()),
        required_rupee_amounts=(3667, 0),
    )
    assert result.has_passed is False
    assert result.mismatched_tokens == ("₹3,676",)


def test_number_audit_explanation_with_the_right_digits_passes() -> None:
    """The twin of the checkpoint case: the engine's ₹3,667 passes."""
    result = NumberAuditService().audit(
        DESIGN_PLAN_A_TEXT,
        AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=()),
        required_rupee_amounts=PLAN_A_REQUIRED_AMOUNTS,
    )
    assert result.has_passed is True
    assert result.failure_reasons == ()
    assert result.mismatched_tokens == ()


def test_number_audit_explanation_with_tamil_digits_passes() -> None:
    """Tamil digits are read as the same figures: ₹௩,௬௬௭ is ₹3,667."""
    text = f"கட்டணமில்லா EMI: ஒவ்வொரு மாதமும் ₹௩,௬௬௭, ௬ மாதங்களுக்கு. கூடுதல் ₹{TAMIL_DIGIT_ZERO}."
    assert audit_plan_a_text(text) == (True, ())


def test_number_audit_explanation_with_price_and_total_in_indian_or_western_grouping_passes() -> (
    None
):
    """₹22,000 has one grouping; ₹23,100 and the plain 23100 forms all read the same value."""
    plan = build_standard_chosen_plan()
    allowed = AllowedNumbers.for_plan_explanation(plan, label_texts=())
    for total_text in ("₹23,100", "Rs. 23100", "23,100 rupees", "INR 23,100.00"):
        text = f"₹3,850 each month for 6 months, ₹1,100 extra, {total_text} in total."
        result = NumberAuditService().audit(text, allowed, required_rupee_amounts=(3850, 1100))
        assert result.has_passed is True, total_text


def test_number_audit_with_indian_and_western_grouping_of_one_amount_passes() -> None:
    """₹1,84,000 and ₹184,000 are the same amount, so both are allowed when it is."""
    allowed = AllowedNumbers(rupee_amounts=frozenset({184_000}), plain_numbers=frozenset())
    for text in ("₹1,84,000 is due.", "₹184,000 is due.", "₹184000 is due."):
        assert NumberAuditService().audit(text, allowed, (184_000,)).has_passed is True


def test_number_audit_with_a_double_zero_fraction_passes_but_paise_fail() -> None:
    """₹3,667.00 is the whole amount; ₹3,666.67 is an unrounded figure and fails."""
    assert audit_plan_a_text(DESIGN_PLAN_A_TEXT.replace("₹3,667", "₹3,667.00")) == (True, ())
    assert audit_plan_a_text(DESIGN_PLAN_A_TEXT.replace("₹3,667", "₹3,666.67"))[1] == ("₹3,666.67",)


def test_number_audit_with_malformed_grouping_fails() -> None:
    """3,6,67 is neither Western nor Indian grouping, so it cannot be trusted."""
    result = NumberAuditService().audit(
        DESIGN_PLAN_A_TEXT.replace("₹3,667", "₹3,6,67"),
        AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=()),
        required_rupee_amounts=(0,),
    )
    assert result.failure_reasons == (NumberAuditFailureReason.MALFORMED_NUMBER,)
    assert result.mismatched_tokens == ("₹3,6,67",)


def test_number_audit_with_magnitude_words_fails() -> None:
    """Plan Q4: "three thousand" and "ஆயிரம்" cannot be checked, so the template is used."""
    for magnitude_text in ("three thousand rupees", "மூன்று ஆயிரம் ரூபாய்"):
        passed, mismatched_tokens = audit_plan_a_text(
            f"{DESIGN_PLAN_A_TEXT} About {magnitude_text}."
        )
        assert passed is False
        assert any(token in {"thousand", "ஆயிரம்"} for token in mismatched_tokens)


def test_number_audit_with_a_tens_word_not_in_the_plan_fails_as_unexpected_plain_number() -> None:
    """The word seventy now reads as 70 (added for spoken amounts), so AI cannot slip it past."""
    result = NumberAuditService().audit(
        f"{DESIGN_PLAN_A_TEXT} Seventy people chose this plan.",
        AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=()),
        required_rupee_amounts=PLAN_A_REQUIRED_AMOUNTS,
    )
    assert result.has_passed is False
    assert result.failure_reasons == (NumberAuditFailureReason.UNEXPECTED_PLAIN_NUMBER,)
    assert result.mismatched_tokens == ("Seventy",)


def test_number_audit_with_a_bare_amount_without_rupee_marker_fails() -> None:
    """3667 without ₹ is a plain number, and plain numbers hold only the tenure here."""
    assert audit_plan_a_text(f"{DESIGN_PLAN_A_TEXT} That is 3667 each month.") == (False, ("3667",))


def test_number_audit_with_the_required_extra_amount_missing_fails() -> None:
    """Plan Q5: the monthly and the extra amount must both be said."""
    result = NumberAuditService().audit(
        "No-cost EMI: you pay ₹3,667 each month for 6 months.",
        AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=()),
        required_rupee_amounts=PLAN_A_REQUIRED_AMOUNTS,
    )
    assert result.failure_reasons == (NumberAuditFailureReason.MISSING_REQUIRED_AMOUNT,)
    assert result.missing_required_amounts == (0,)


def test_number_audit_with_a_percent_sign_fails() -> None:
    """Ratios are never AI material (plan Q3), and a % cannot be checked."""
    passed, mismatched_tokens = audit_plan_a_text(f"{DESIGN_PLAN_A_TEXT} That is 6% of it.")
    assert passed is False
    assert "%" in mismatched_tokens


def test_number_audit_with_forbidden_wording_fails_even_with_right_numbers() -> None:
    """Right figures do not excuse a credit-decision word."""
    result = NumberAuditService().audit(
        f"{DESIGN_PLAN_A_TEXT} You are approved.",
        AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=()),
        required_rupee_amounts=PLAN_A_REQUIRED_AMOUNTS,
    )
    assert result.failure_reasons == (NumberAuditFailureReason.FORBIDDEN_WORDING,)
    assert result.forbidden_phrases == ("approved",)


def test_number_audit_with_empty_text_fails() -> None:
    """No text is never a pass, even with nothing required."""
    allowed = AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=())
    for text in ("", "   \n"):
        result = NumberAuditService().audit(text, allowed, required_rupee_amounts=())
        assert result.failure_reasons == (NumberAuditFailureReason.EMPTY_TEXT,)


def test_number_audit_failure_reasons_are_listed_once_in_first_seen_order() -> None:
    """Two wrong amounts give one reason; each kind of failure is named."""
    result = NumberAuditService().audit(
        "₹1 and ₹2 for 7 months, the best plan.",
        AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=()),
        required_rupee_amounts=(3667,),
    )
    assert result.failure_reasons == (
        NumberAuditFailureReason.UNEXPECTED_RUPEE_AMOUNT,
        NumberAuditFailureReason.UNEXPECTED_PLAIN_NUMBER,
        NumberAuditFailureReason.MISSING_REQUIRED_AMOUNT,
        NumberAuditFailureReason.FORBIDDEN_WORDING,
    )
    assert result.mismatched_tokens == ("₹1", "₹2", "7")


def test_number_audit_same_inputs_give_the_same_result() -> None:
    """The audit is deterministic, so a fallback decision can be reproduced."""
    allowed = AllowedNumbers.for_plan_explanation(design_plan_a(), label_texts=("Brand",))
    text = DESIGN_PLAN_A_TEXT.replace("₹0", "₹10")
    first_result = NumberAuditService().audit(text, allowed, PLAN_A_REQUIRED_AMOUNTS)
    assert NumberAuditService().audit(text, allowed, PLAN_A_REQUIRED_AMOUNTS) == first_result


def test_number_audit_template_explanation_text_passes_in_both_languages() -> None:
    """The standard C7 text, which AI text replaces, holds only figures the audit allows."""
    template = TemplateExplanationService(format_paise_as_whole_rupees)
    for plan in (design_plan_a(), build_standard_chosen_plan()):
        allowed = AllowedNumbers.for_plan_explanation(plan, label_texts=(plan.lender_label,))
        required = (
            whole_rupees_of(plan.monthly_installment),
            whole_rupees_of(plan.extra_in_total),
        )
        for language in CustomerLanguage:
            text = template.explain(plan, language).text
            assert NumberAuditService().audit(text, allowed, required).has_passed is True, text


@given(
    monthly_in_paise=st.integers(min_value=100, max_value=10_000_000_000),
    extra_in_paise=st.integers(min_value=0, max_value=10_000_000_000),
    price_in_paise=st.integers(min_value=100, max_value=10_000_000_000),
    tenure_in_months=st.integers(min_value=1, max_value=60),
    data=st.data(),
)
def test_number_audit_changing_any_single_digit_of_an_allowed_amount_fails(
    monthly_in_paise: int,
    extra_in_paise: int,
    price_in_paise: int,
    tenure_in_months: int,
    data: st.DataObject,
) -> None:
    """Any one-digit change to any amount in a passing text is caught, unless it hits another."""
    plan = ChosenPlan(
        offer_id="offer-property",
        plan_kind=EmiType.STANDARD,
        lender_label="Lender",
        tenure_in_months=tenure_in_months,
        monthly_installment=Money.from_paise(monthly_in_paise),
        extra_in_total=Money.from_paise(extra_in_paise),
        total_payable=Money.from_paise(price_in_paise + extra_in_paise),
    )
    allowed = AllowedNumbers.for_plan_explanation(plan, label_texts=())
    monthly_text, extra_text, total_text = (
        format_paise_as_whole_rupees(amount.to_paise())
        for amount in (plan.monthly_installment, plan.extra_in_total, plan.total_payable)
    )
    text = (
        f"You pay {monthly_text} each month for {tenure_in_months} months. "
        f"The extra you pay in total is {extra_text}, and {total_text} in all."
    )
    assert NumberAuditService().audit(text, allowed, ()).has_passed is True
    amount_match = data.draw(st.sampled_from(list(RUPEE_AMOUNT_PATTERN.finditer(text))))
    digit_positions = [
        position
        for position in range(amount_match.start(), amount_match.end())
        if text[position].isdigit()
    ]
    position = data.draw(st.sampled_from(digit_positions))
    new_digit = data.draw(
        st.sampled_from([digit for digit in "0123456789" if digit != text[position]])
    )
    changed_text = text[:position] + new_digit + text[position + 1 :]
    changed_amount = changed_text[amount_match.start() : amount_match.end()]
    assume(int(changed_amount[1:].replace(",", "")) not in allowed.rupee_amounts)
    result = NumberAuditService().audit(changed_text, allowed, ())
    assert result.has_passed is False
    assert result.mismatched_tokens == (changed_amount,)
