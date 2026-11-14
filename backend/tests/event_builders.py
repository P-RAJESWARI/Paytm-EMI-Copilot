"""Builders of one valid instance of every domain event, with synthetic ids only."""

from emi_copilot.domain.events import (
    DomainEvent,
    OfferQuoteMismatch,
    PaymentLinkCreated,
    PaymentLinkCreationFailed,
    PaymentLinkOutcomeUnknown,
    PaymentStatusChanged,
    StatusReportSource,
    WebhookOutcome,
    WebhookProcessed,
    WebhookRejected,
)
from emi_copilot.domain.payments import (
    GatewayPaymentStatus,
    PaymentAttemptStatus,
    PaymentLinkFailureCode,
)
from tests.payment_builders import CREATED_AT

SAMPLE_ATTEMPT_ID = "01JCSAMPLEATTEMPT000000001"
SAMPLE_ORDER_ID = "ORDER-SAMPLE-0001"


def build_every_domain_event() -> list[DomainEvent]:
    """Gives one event of each of the seven types, in a fixed order."""
    link_fields = {
        "occurred_at": CREATED_AT,
        "payment_attempt_id": SAMPLE_ATTEMPT_ID,
        "order_id": SAMPLE_ORDER_ID,
        "offer_id": "offer-plan-a",
        "amount_in_paise": 2_200_000,
        "gateway_mode": "mock",
    }
    return [
        PaymentLinkCreated(**link_fields),  # type: ignore[arg-type]
        PaymentLinkCreationFailed(
            **link_fields,  # type: ignore[arg-type]
            failure_code=PaymentLinkFailureCode.GATEWAY_UNAVAILABLE,
        ),
        PaymentLinkOutcomeUnknown(
            **link_fields,  # type: ignore[arg-type]
            cause_error_code="PAYMENT_GATEWAY_TIMEOUT",
        ),
        build_payment_status_changed(),
        WebhookRejected(
            occurred_at=CREATED_AT,
            webhook_delivery_id="01JCSAMPLEDELIVERY00000001",
            rejection_code="WEBHOOK_SIGNATURE_INVALID",
        ),
        WebhookProcessed(
            occurred_at=CREATED_AT,
            order_id="ORDER-UNKNOWN-0001",
            outcome=WebhookOutcome.UNKNOWN_ORDER,
            reported_status=GatewayPaymentStatus.PAID,
            amount_paid_in_paise=2_100_000,
            gateway_transaction_id="transaction-sample-0001",
        ),
        OfferQuoteMismatch(
            occurred_at=CREATED_AT,
            offer_id="offer-plan-b",
            tenure_in_months=6,
            price_in_paise=2_200_000,
            quoted_monthly_installment_in_paise=400_000,
            schedule_regular_installment_in_paise=385_000,
            quoted_extra_in_total_in_paise=110_000,
        ),
    ]


def build_payment_status_changed() -> PaymentStatusChanged:
    """A webhook that marked the sample attempt PAID, for less than the link amount."""
    return PaymentStatusChanged(
        occurred_at=CREATED_AT,
        payment_attempt_id=SAMPLE_ATTEMPT_ID,
        order_id=SAMPLE_ORDER_ID,
        previous_status=PaymentAttemptStatus.LINK_CREATED,
        new_status=PaymentAttemptStatus.PAID,
        reported_status=GatewayPaymentStatus.PAID,
        source=StatusReportSource.WEBHOOK,
        amount_in_paise=2_200_000,
        amount_paid_in_paise=2_100_000,
        gateway_transaction_id="transaction-sample-0001",
    )
