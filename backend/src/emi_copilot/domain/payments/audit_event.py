"""AuditEvent: one append-only evidence record of something that happened on the payment path."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from emi_copilot.domain.errors import InvalidAuditEventError
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_optional_non_empty_text,
    require_timezone_aware_moment,
)

AuditDetailValue = str | int | bool | None
"""A JSON scalar. Floats are excluded so money can never reach the audit trail as a float."""


class AuditEventType(StrEnum):
    """What an audit event records; stored by value, so a rename needs a migration."""

    PAYMENT_LINK_CREATED = "PAYMENT_LINK_CREATED"
    PAYMENT_LINK_CREATION_FAILED = "PAYMENT_LINK_CREATION_FAILED"
    PAYMENT_LINK_OUTCOME_UNKNOWN = "PAYMENT_LINK_OUTCOME_UNKNOWN"
    PAYMENT_STATUS_CHANGED = "PAYMENT_STATUS_CHANGED"
    WEBHOOK_REJECTED = "WEBHOOK_REJECTED"
    WEBHOOK_PROCESSED = "WEBHOOK_PROCESSED"
    OFFER_QUOTE_MISMATCH = "OFFER_QUOTE_MISMATCH"


def _freeze_details(details: object) -> Mapping[str, AuditDetailValue]:
    """Copies details into a read-only mapping once every key is text and every value a scalar."""
    if not isinstance(details, Mapping):
        raise InvalidAuditEventError("Audit details must be a mapping of text to JSON scalars.")
    for key, value in details.items():
        require_non_empty_text(key, "audit detail key", InvalidAuditEventError)
        if value is not None and not isinstance(value, str | int):
            raise InvalidAuditEventError(
                f"The audit detail {key!r} must be text, an integer, a bool or None."
            )
    return MappingProxyType(dict(details))


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """An immutable fact about a subject, such as a payment attempt; written once, never changed.

    Details hold identifiers, statuses, reason codes and integer paise only. They must never hold
    personal data (names, phone numbers, income), tokens, OTPs, signatures or checksums, secrets,
    card fields or raw vendor payloads (security-and-compliance.md sections 2, 3 and 9).
    """

    id: str
    event_type: AuditEventType
    subject_type: str
    subject_id: str
    correlation_id: str | None
    occurred_at: datetime
    details: Mapping[str, AuditDetailValue] = field(
        default_factory=lambda: MappingProxyType({}), hash=False
    )

    def __post_init__(self) -> None:
        """Rejects missing identifiers, an unknown type, a naive timestamp or non-scalar details."""
        require_non_empty_text(self.id, "audit event id", InvalidAuditEventError)
        if not isinstance(self.event_type, AuditEventType):
            raise InvalidAuditEventError("The event type must be an AuditEventType.")
        require_non_empty_text(self.subject_type, "subject type", InvalidAuditEventError)
        require_non_empty_text(self.subject_id, "subject id", InvalidAuditEventError)
        require_optional_non_empty_text(
            self.correlation_id, "correlation id", InvalidAuditEventError
        )
        require_timezone_aware_moment(self.occurred_at, "occurred at", InvalidAuditEventError)
        object.__setattr__(self, "details", _freeze_details(self.details))
