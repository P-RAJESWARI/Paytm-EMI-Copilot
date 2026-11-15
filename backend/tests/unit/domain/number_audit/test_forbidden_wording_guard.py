"""ForbiddenWordingGuard: credit-decision, rate, push and band words never pass in AI text."""

import pytest

from emi_copilot.domain.number_audit import (
    AllowedNumbers,
    ForbiddenWordingGuard,
    NumberAuditFailureReason,
    NumberAuditService,
)
from emi_copilot.domain.number_audit.forbidden_wording_guard import (
    FORBIDDEN_ENGLISH_PHRASES,
    FORBIDDEN_TAMIL_PHRASES,
)
from tests.sale_builders import build_no_cost_chosen_plan

PASSING_TEXT = (
    "No-cost EMI: you pay ₹3,667 each month for 6 months. The extra you pay in total is ₹0."
)


@pytest.mark.parametrize("phrase", [*FORBIDDEN_ENGLISH_PHRASES, *FORBIDDEN_TAMIL_PHRASES])
def test_number_audit_with_each_forbidden_phrase_fails(phrase: str) -> None:
    """Every listed phrase makes otherwise correct text fall back to the template."""
    result = NumberAuditService().audit(
        f"{PASSING_TEXT} {phrase}.",
        AllowedNumbers.for_plan_explanation(build_no_cost_chosen_plan(), label_texts=()),
        required_rupee_amounts=(3667, 0),
    )
    assert result.failure_reasons == (NumberAuditFailureReason.FORBIDDEN_WORDING,)
    assert result.forbidden_phrases == (phrase,)


@pytest.mark.parametrize(
    ("text", "expected_phrases"),
    [
        ("This is the BEST FOR YOU.", ("BEST FOR YOU",)),
        ("An interest\n rate applies.", ("interest\n rate",)),
        ("Comfortable, risky.", ("Comfortable", "risky")),
        ("இது வசதியானது", ("வசதியானது",)),
    ],
)
def test_forbidden_wording_guard_ignores_case_and_spacing(
    text: str, expected_phrases: tuple[str, ...]
) -> None:
    """Capitals and line breaks do not hide a phrase; it is quoted as written."""
    assert ForbiddenWordingGuard().find_forbidden_phrases(text) == expected_phrases


@pytest.mark.parametrize(
    "text",
    [
        PASSING_TEXT,
        "An interesting rate card.",
        "Comfortably within the price.",
        "Disapproved and preapproved are other words.",
    ],
)
def test_forbidden_wording_guard_allows_plain_text_and_longer_words(text: str) -> None:
    """Whole words only, so ordinary text with similar letters is not refused."""
    assert ForbiddenWordingGuard().find_forbidden_phrases(text) == ()
