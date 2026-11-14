"""Tests for PaymentStatusService: server-side checks and idempotent, verified webhooks."""

import pytest

from emi_copilot.domain.errors import (
    InvalidPaymentGatewayValueError,
    PaymentAttemptNotFoundError,
    WebhookSignatureInvalidError,
)
from emi_copilot.domain.events import WebhookOutcome
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    AuditEventType,
    GatewayPaymentStatus,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatusResult,
    VerifiedWebhookEvent,
)
from emi_copilot.services.payment_status_service import PaymentStatusService
from tests.fakes.fake_payment_gateway import build_signed_notification
from tests.payment_builders import build_payment_attempt
from tests.unit.services.conftest import ServiceTestKit

ORDER_ID = "ORDER-SAMPLE-0001"
TRANSACTION_ID = "transaction-sample-0001"
LINK_AMOUNT = Money.from_rupees("22000")
DISCOUNTED_AMOUNT_PAID = Money.from_rupees("21000")


def _build_service(kit: ServiceTestKit) -> PaymentStatusService:
    """Wires the service on the kit's fakes."""
    return PaymentStatusService(
        kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.id_generator, kit.event_bus
    )


def _store_attempt(
    kit: ServiceTestKit, status: PaymentAttemptStatus = PaymentAttemptStatus.LINK_CREATED
) -> PaymentAttempt:
    """Stores the sample attempt with a link, in the given status."""
    payment_attempt = build_payment_attempt(
        status=status,
        gateway_link_id="link-sample-0001",
        payment_link_url="https://fake-gateway.invalid/pay/sample",
    )
    kit.store_attempt(payment_attempt)
    return payment_attempt


def _script_status(
    kit: ServiceTestKit, status: GatewayPaymentStatus, amount_paid: Money | None = None
) -> None:
    """Makes the fake gateway report a status for the sample order."""
    kit.payment_gateway.status_results_by_order_id[ORDER_ID] = PaymentStatusResult(
        order_id=ORDER_ID,
        status=status,
        gateway_transaction_id=None if status is GatewayPaymentStatus.NOT_FOUND else TRANSACTION_ID,
        amount_paid=amount_paid,
    )


def _script_webhook(
    kit: ServiceTestKit,
    status: GatewayPaymentStatus = GatewayPaymentStatus.PAID,
    order_id: str = ORDER_ID,
    amount_paid: Money | None = LINK_AMOUNT,
) -> str:
    """Makes the fake gateway accept one signature as a verified event; returns the signature."""
    signature = f"valid-signature-{len(kit.payment_gateway.verified_events_by_signature)}"
    kit.payment_gateway.verified_events_by_signature[signature] = VerifiedWebhookEvent(
        order_id=order_id,
        status=status,
        gateway_transaction_id=TRANSACTION_ID,
        amount_paid=amount_paid if status is GatewayPaymentStatus.PAID else None,
    )
    return signature


def test_get_payment_status_for_an_unknown_order_raises_without_asking_the_gateway(
    kit: ServiceTestKit,
) -> None:
    """Only our own orders are checked, so nobody can probe the gateway through us."""
    with pytest.raises(PaymentAttemptNotFoundError):
        _build_service(kit).get_payment_status("ORDER-UNKNOWN-0001")
    assert kit.payment_gateway.status_check_calls == []


def test_get_payment_status_paid_moves_the_attempt_and_audits_the_change(
    kit: ServiceTestKit,
) -> None:
    """A server-side PAID marks the attempt PAID with its transaction id, audited once."""
    _store_attempt(kit)
    _script_status(kit, GatewayPaymentStatus.PAID, LINK_AMOUNT)
    status_view = _build_service(kit).get_payment_status(ORDER_ID)
    assert (status_view.status, status_view.amount, status_view.amount_paid) == (
        PaymentAttemptStatus.PAID,
        LINK_AMOUNT,
        LINK_AMOUNT,
    )
    assert kit.only_attempt().gateway_transaction_id == TRANSACTION_ID
    assert kit.audit_event_types() == [AuditEventType.PAYMENT_STATUS_CHANGED]
    assert dict(kit.last_audit_event().details) == {
        "order_id": ORDER_ID,
        "previous_status": "LINK_CREATED",
        "new_status": "PAID",
        "reported_status": "PAID",
        "source": "STATUS_CHECK",
        "amount_in_paise": 2_200_000,
        "amount_paid_in_paise": 2_200_000,
        "gateway_transaction_id": TRANSACTION_ID,
    }


@pytest.mark.parametrize(
    ("stored_status", "reported_status"),
    [
        (PaymentAttemptStatus.PAID, GatewayPaymentStatus.FAILED),
        (PaymentAttemptStatus.PAID, GatewayPaymentStatus.PENDING),
        (PaymentAttemptStatus.LINK_CREATED, GatewayPaymentStatus.NOT_FOUND),
        (PaymentAttemptStatus.PAYMENT_PENDING, GatewayPaymentStatus.PENDING),
    ],
)
def test_get_payment_status_without_a_change_writes_nothing(
    kit: ServiceTestKit,
    stored_status: PaymentAttemptStatus,
    reported_status: GatewayPaymentStatus,
) -> None:
    """PAID is never downgraded, NOT_FOUND changes nothing, and a repeat writes no row."""
    stored_attempt = _store_attempt(kit, stored_status)
    _script_status(kit, reported_status)
    status_view = _build_service(kit).get_payment_status(ORDER_ID)
    assert status_view.status is stored_status
    assert kit.only_attempt() == stored_attempt
    assert kit.database.audit_events == []


def test_apply_webhook_with_a_bad_signature_is_audited_and_reraised(kit: ServiceTestKit) -> None:
    """A forged notification is refused, recorded as WEBHOOK_REJECTED and changes nothing."""
    stored_attempt = _store_attempt(kit)
    with pytest.raises(WebhookSignatureInvalidError):
        _build_service(kit).apply_webhook(build_signed_notification("forged-signature"))
    assert kit.only_attempt() == stored_attempt
    assert kit.audit_event_types() == [AuditEventType.WEBHOOK_REJECTED]
    rejected_audit = kit.last_audit_event()
    assert rejected_audit.subject_type == "webhook_delivery"
    assert rejected_audit.subject_id == "01JCTESTID0000000000000001"
    assert dict(rejected_audit.details) == {"rejection_code": "WEBHOOK_SIGNATURE_INVALID"}


def test_apply_webhook_signed_but_malformed_is_audited_and_reraised(kit: ServiceTestKit) -> None:
    """A genuine but unreadable notification is refused the same way, with its own code."""
    kit.payment_gateway.malformed_signatures.add("malformed-signature")
    with pytest.raises(InvalidPaymentGatewayValueError):
        _build_service(kit).apply_webhook(build_signed_notification("malformed-signature"))
    assert kit.last_audit_event().details["rejection_code"] == "INVALID_PAYMENT_GATEWAY_VALUE"


def test_apply_webhook_paid_moves_the_attempt_once_and_a_repeat_writes_nothing(
    kit: ServiceTestKit,
) -> None:
    """The first delivery changes the status; the identical second one adds no row at all."""
    _store_attempt(kit)
    signature = _script_webhook(kit)
    service = _build_service(kit)
    first_application = service.apply_webhook(build_signed_notification(signature))
    paid_attempt = kit.only_attempt()
    audit_rows_after_first = list(kit.database.audit_events)
    repeated_application = service.apply_webhook(build_signed_notification(signature))
    assert (first_application.outcome, first_application.status) == (
        WebhookOutcome.STATUS_CHANGED,
        PaymentAttemptStatus.PAID,
    )
    assert (repeated_application.outcome, repeated_application.status) == (
        WebhookOutcome.NO_CHANGE,
        PaymentAttemptStatus.PAID,
    )
    assert kit.only_attempt() == paid_attempt
    assert kit.database.audit_events == audit_rows_after_first
    assert kit.audit_event_types() == [AuditEventType.PAYMENT_STATUS_CHANGED]
    assert kit.last_audit_event().details["source"] == "WEBHOOK"


def test_apply_webhook_with_a_lower_paid_amount_is_accepted_and_both_amounts_recorded(
    kit: ServiceTestKit,
) -> None:
    """A discount can lower what is paid, so the webhook is applied and both amounts audited."""
    _store_attempt(kit)
    signature = _script_webhook(kit, amount_paid=DISCOUNTED_AMOUNT_PAID)
    application = _build_service(kit).apply_webhook(build_signed_notification(signature))
    assert application.status is PaymentAttemptStatus.PAID
    details = kit.last_audit_event().details
    assert (details["amount_in_paise"], details["amount_paid_in_paise"]) == (2_200_000, 2_100_000)


def test_apply_webhook_failed_after_paid_never_downgrades(kit: ServiceTestKit) -> None:
    """A late FAILED delivery for a paid order is no change and writes nothing."""
    stored_attempt = _store_attempt(kit, PaymentAttemptStatus.PAID)
    signature = _script_webhook(kit, GatewayPaymentStatus.FAILED)
    application = _build_service(kit).apply_webhook(build_signed_notification(signature))
    assert application.outcome is WebhookOutcome.NO_CHANGE
    assert kit.only_attempt() == stored_attempt
    assert kit.database.audit_events == []


def test_apply_webhook_for_an_unknown_order_is_audited_without_any_state_change(
    kit: ServiceTestKit,
) -> None:
    """A verified webhook about an order that is not ours records WEBHOOK_PROCESSED only."""
    signature = _script_webhook(kit, order_id="ORDER-UNKNOWN-0001")
    application = _build_service(kit).apply_webhook(build_signed_notification(signature))
    assert (application.order_id, application.outcome, application.status) == (
        "ORDER-UNKNOWN-0001",
        WebhookOutcome.UNKNOWN_ORDER,
        None,
    )
    assert kit.database.payment_attempts_by_id == {}
    assert kit.audit_event_types() == [AuditEventType.WEBHOOK_PROCESSED]
    processed_audit = kit.last_audit_event()
    assert (processed_audit.subject_type, processed_audit.subject_id) == (
        "payment_order",
        "ORDER-UNKNOWN-0001",
    )
    assert processed_audit.details["outcome"] == "UNKNOWN_ORDER"
    assert processed_audit.details["amount_paid_in_paise"] == 2_200_000


@pytest.mark.parametrize(
    ("reported_status", "expected_status"),
    [
        (GatewayPaymentStatus.PAID, PaymentAttemptStatus.PAID),
        (GatewayPaymentStatus.PENDING, PaymentAttemptStatus.PAYMENT_PENDING),
        (GatewayPaymentStatus.FAILED, PaymentAttemptStatus.PAYMENT_FAILED),
    ],
)
def test_apply_webhook_moves_an_attempt_whose_create_outcome_was_never_recorded(
    kit: ServiceTestKit,
    reported_status: GatewayPaymentStatus,
    expected_status: PaymentAttemptStatus,
) -> None:
    """A report on an in-progress attempt proves its link exists, so it is applied and audited."""
    kit.store_attempt(build_payment_attempt(status=PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS))
    signature = _script_webhook(kit, reported_status)
    application = _build_service(kit).apply_webhook(build_signed_notification(signature))
    assert (application.outcome, application.status) == (
        WebhookOutcome.STATUS_CHANGED,
        expected_status,
    )
    assert kit.only_attempt().status is expected_status
    assert kit.audit_event_types() == [AuditEventType.PAYMENT_STATUS_CHANGED]
    details = kit.last_audit_event().details
    assert (details["previous_status"], details["new_status"]) == (
        "LINK_CREATION_IN_PROGRESS",
        expected_status.value,
    )
