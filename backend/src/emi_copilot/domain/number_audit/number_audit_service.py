"""NumberAuditService: checks every number and phrase of AI text before anyone sees it (rule 2).

Any failure means the caller shows the template text instead; the audit never repairs text.
"""

from dataclasses import dataclass
from enum import StrEnum

from emi_copilot.domain.number_audit.allowed_numbers import AllowedNumbers
from emi_copilot.domain.number_audit.forbidden_wording_guard import ForbiddenWordingGuard
from emi_copilot.domain.number_audit.number_token import NumberToken, NumberTokenKind
from emi_copilot.domain.number_audit.number_token_extractor import NumberTokenExtractor


class NumberAuditFailureReason(StrEnum):
    """Why an AI text failed the audit; recorded as evidence, never shown to a customer."""

    UNEXPECTED_RUPEE_AMOUNT = "UNEXPECTED_RUPEE_AMOUNT"
    UNEXPECTED_PLAIN_NUMBER = "UNEXPECTED_PLAIN_NUMBER"
    MALFORMED_NUMBER = "MALFORMED_NUMBER"
    UNCHECKABLE_NUMBER = "UNCHECKABLE_NUMBER"
    MISSING_REQUIRED_AMOUNT = "MISSING_REQUIRED_AMOUNT"
    EMPTY_TEXT = "EMPTY_TEXT"
    FORBIDDEN_WORDING = "FORBIDDEN_WORDING"


@dataclass(frozen=True, slots=True)
class NumberAuditResult:
    """The audit verdict: failure reasons in first-seen order, and what caused them."""

    failure_reasons: tuple[NumberAuditFailureReason, ...]
    mismatched_tokens: tuple[str, ...]
    missing_required_amounts: tuple[int, ...]
    forbidden_phrases: tuple[str, ...]

    @property
    def has_passed(self) -> bool:
        """Tells whether the text may be shown: no failure of any kind was found."""
        return not self.failure_reasons


def find_token_failure(
    token: NumberToken, allowed: AllowedNumbers
) -> NumberAuditFailureReason | None:
    """Gives why one number fails, or None when it is one of the allowed figures."""
    if token.kind is NumberTokenKind.MALFORMED:
        return NumberAuditFailureReason.MALFORMED_NUMBER
    if token.kind is NumberTokenKind.UNCHECKABLE:
        return NumberAuditFailureReason.UNCHECKABLE_NUMBER
    if token.kind is NumberTokenKind.RUPEE_AMOUNT:
        if token.value in allowed.rupee_amounts:
            return None
        return NumberAuditFailureReason.UNEXPECTED_RUPEE_AMOUNT
    if token.value in allowed.plain_numbers:
        return None
    return NumberAuditFailureReason.UNEXPECTED_PLAIN_NUMBER


class NumberAuditService:
    """Checks AI text for allowed figures only, every required amount and no forbidden word."""

    def __init__(self) -> None:
        """Builds the stateless extractor and wording guard it uses."""
        self._extractor = NumberTokenExtractor()
        self._wording_guard = ForbiddenWordingGuard()

    def audit(
        self, text: str, allowed: AllowedNumbers, required_rupee_amounts: tuple[int, ...]
    ) -> NumberAuditResult:
        """Audits the text; the same inputs always give the same result."""
        if not text.strip():
            return NumberAuditResult((NumberAuditFailureReason.EMPTY_TEXT,), (), (), ())
        tokens = self._extractor.extract(text)
        token_failures = [
            (failure_reason, token.text)
            for token in tokens
            if (failure_reason := find_token_failure(token, allowed)) is not None
        ]
        reasons = [failure_reason for failure_reason, _ in token_failures]
        mentioned_amounts = {
            token.value for token in tokens if token.kind is NumberTokenKind.RUPEE_AMOUNT
        }
        missing_amounts = tuple(
            amount for amount in required_rupee_amounts if amount not in mentioned_amounts
        )
        if missing_amounts:
            reasons.append(NumberAuditFailureReason.MISSING_REQUIRED_AMOUNT)
        forbidden_phrases = self._wording_guard.find_forbidden_phrases(text)
        if forbidden_phrases:
            reasons.append(NumberAuditFailureReason.FORBIDDEN_WORDING)
        return NumberAuditResult(
            failure_reasons=tuple(dict.fromkeys(reasons)),
            mismatched_tokens=tuple(token_text for _, token_text in token_failures),
            missing_required_amounts=missing_amounts,
            forbidden_phrases=forbidden_phrases,
        )
