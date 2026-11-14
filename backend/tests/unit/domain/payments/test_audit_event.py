"""Tests for the AuditEvent record and its read-only, scalar-only details."""

from datetime import datetime

import pytest

from emi_copilot.domain.errors import InvalidAuditEventError
from emi_copilot.domain.payments import AuditEvent, AuditEventType
from tests.payment_builders import CREATED_AT, build_audit_event


def test_audit_event_with_scalar_details_keeps_them() -> None:
    """Text, integer, bool and None details are kept as given."""
    audit_event = build_audit_event(
        details={
            "reason_code": "SIGNATURE_MISMATCH",
            "amount_in_paise": 5,
            "is_replay": False,
            "gateway_link_id": None,
        }
    )
    assert dict(audit_event.details) == {
        "reason_code": "SIGNATURE_MISMATCH",
        "amount_in_paise": 5,
        "is_replay": False,
        "gateway_link_id": None,
    }


def test_audit_event_without_details_has_empty_details() -> None:
    """Details are optional and default to an empty mapping."""
    audit_event = AuditEvent(
        id="01JCSAMPLEAUDITEVENT000009",
        event_type=AuditEventType.WEBHOOK_REJECTED,
        subject_type="webhook",
        subject_id="ORDER-SAMPLE-0001",
        correlation_id=None,
        occurred_at=CREATED_AT,
    )
    assert dict(audit_event.details) == {}


def test_audit_event_details_are_a_read_only_copy() -> None:
    """Changing the caller's dictionary later, or the details directly, cannot alter evidence."""
    caller_details: dict[str, str | int | bool | None] = {"status": "PAID"}
    audit_event = build_audit_event(details=caller_details)
    caller_details["status"] = "PAYMENT_FAILED"
    assert audit_event.details["status"] == "PAID"
    with pytest.raises(TypeError):
        audit_event.details["status"] = "PAYMENT_FAILED"  # type: ignore[index]


def test_audit_events_with_same_fields_are_equal() -> None:
    """Two events built from the same values compare equal, including their details."""
    assert build_audit_event() == build_audit_event()


@pytest.mark.parametrize(
    ("field_overrides", "expected_message"),
    [
        ({"id": ""}, "audit event id"),
        ({"event_type": "PAYMENT_LINK_CREATED"}, "AuditEventType"),
        ({"subject_type": " "}, "subject type"),
        ({"subject_id": None}, "subject id"),
        ({"correlation_id": ""}, "correlation id"),
        ({"occurred_at": datetime(2026, 11, 14)}, "occurred at"),  # noqa: DTZ001
        ({"details": [("status", "PAID")]}, "mapping"),
        ({"details": {"": "PAID"}}, "audit detail key"),
        ({"details": {7: "PAID"}}, "audit detail key"),
        ({"details": {"amount_in_rupees": 22000.0}}, "'amount_in_rupees'"),
        ({"details": {"raw_payload": {"nested": "value"}}}, "'raw_payload'"),
    ],
)
def test_audit_event_with_invalid_field_raises_invalid_audit_event_error(
    field_overrides: dict[str, object], expected_message: str
) -> None:
    """Missing identifiers, naive timestamps, floats and nested payloads are rejected."""
    with pytest.raises(InvalidAuditEventError, match=expected_message):
        build_audit_event(**field_overrides)


def test_audit_event_type_values_are_stable_stored_words() -> None:
    """Event types are stored by value and checked by the database, so values equal names."""
    assert all(event_type.value == event_type.name for event_type in AuditEventType)
    assert len(AuditEventType) == 7
