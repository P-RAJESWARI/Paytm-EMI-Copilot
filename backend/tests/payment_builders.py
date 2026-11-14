"""Builders of valid payment domain objects with synthetic values; tests override single fields."""

from dataclasses import replace
from datetime import UTC, datetime

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    AuditEvent,
    AuditEventType,
    EmiType,
    OfferSnapshot,
    PaymentAttempt,
    PaymentAttemptStatus,
)

CREATED_AT = datetime(2026, 11, 14, 10, 30, 0, 123456, tzinfo=UTC)
SAMPLE_REQUEST_FINGERPRINT = "a" * 64


def build_no_cost_offer_snapshot() -> OfferSnapshot:
    """Design plan A on ₹22,000: no-cost, 5 x ₹3,666.67 then ₹3,666.65, nothing extra."""
    return OfferSnapshot(
        offer_id="offer-plan-a",
        lender_label="Brand",
        emi_type=EmiType.NO_COST,
        tenure_in_months=6,
        regular_installment=Money.from_rupees("3666.67"),
        last_installment=Money.from_rupees("3666.65"),
        total_payable=Money.from_rupees("22000"),
        extra_in_total=Money.from_paise(0),
    )


def build_standard_offer_snapshot() -> OfferSnapshot:
    """Design plan B on ₹22,000: 6 x ₹3,850.00 with ₹1,100 extra in total."""
    return OfferSnapshot(
        offer_id="offer-plan-b",
        lender_label="Your card's bank",
        emi_type=EmiType.STANDARD,
        tenure_in_months=6,
        regular_installment=Money.from_rupees("3850.00"),
        last_installment=Money.from_rupees("3850.00"),
        total_payable=Money.from_rupees("23100"),
        extra_in_total=Money.from_rupees("1100"),
    )


def build_payment_attempt(attempt_number: int = 1, /, **overrides: object) -> PaymentAttempt:
    """Builds a valid attempt whose id, order id and key are unique per attempt number."""
    payment_attempt = PaymentAttempt(
        id=f"01JCSAMPLEATTEMPT{attempt_number:09d}",
        order_id=f"ORDER-SAMPLE-{attempt_number:04d}",
        idempotency_key=f"idempotency-key-sample-{attempt_number:04d}",
        request_fingerprint=SAMPLE_REQUEST_FINGERPRINT,
        amount=Money.from_rupees("22000"),
        status=PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS,
        offer_snapshot=build_no_cost_offer_snapshot(),
        gateway_mode="mock",
        gateway_link_id=None,
        payment_link_url=None,
        gateway_transaction_id=None,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )
    return replace(payment_attempt, **overrides)  # type: ignore[arg-type]


def build_audit_event(event_number: int = 1, /, **overrides: object) -> AuditEvent:
    """Builds a valid audit event about the first sample payment attempt."""
    audit_event = AuditEvent(
        id=f"01JCSAMPLEAUDITEVENT{event_number:06d}",
        event_type=AuditEventType.PAYMENT_LINK_CREATED,
        subject_type="payment_attempt",
        subject_id=build_payment_attempt().id,
        correlation_id="correlation-sample-0001",
        occurred_at=CREATED_AT,
        details={"status": "LINK_CREATED", "amount_in_paise": 2_200_000},
    )
    return replace(audit_event, **overrides)  # type: ignore[arg-type]
