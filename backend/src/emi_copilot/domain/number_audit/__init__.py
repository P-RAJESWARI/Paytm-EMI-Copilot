"""Number audit (plan step 4.2, ADR 0024): every number in AI text must be an engine figure.

Pure domain code. Services audit AI text here before it is shown, and fall back to the template
text on any failure (CLAUDE.md rule 2).
"""

from emi_copilot.domain.number_audit.allowed_numbers import AllowedNumbers
from emi_copilot.domain.number_audit.forbidden_wording_guard import ForbiddenWordingGuard
from emi_copilot.domain.number_audit.number_audit_service import (
    NumberAuditFailureReason,
    NumberAuditResult,
    NumberAuditService,
)
from emi_copilot.domain.number_audit.number_token import NumberToken, NumberTokenKind
from emi_copilot.domain.number_audit.number_token_extractor import NumberTokenExtractor

__all__ = [
    "AllowedNumbers",
    "ForbiddenWordingGuard",
    "NumberAuditFailureReason",
    "NumberAuditResult",
    "NumberAuditService",
    "NumberToken",
    "NumberTokenExtractor",
    "NumberTokenKind",
]
