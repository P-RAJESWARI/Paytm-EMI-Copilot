"""Domain events: immutable facts that services publish and subscribers, such as audit, record.

Every field is an id, a status, a code or an amount in integer paise. An event never holds
personal data, card fields, secrets, signatures or vendor payloads, so any subscriber may store
it as it is (security-and-compliance.md sections 2, 3 and 9).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from emi_copilot.domain.errors import PaymentLinkFailureCode
from emi_copilot.domain.payments.gateway_payment_status import GatewayPaymentStatus
from emi_copilot.domain.payments.payment_attempt_status import PaymentAttemptStatus
from emi_copilot.domain.sales.sale_state_machine import SalePaymentOutcome
from emi_copilot.domain.sales.sale_status import SaleStatus


class StatusReportSource(StrEnum):
    """Where a gateway report about a payment came from."""

    STATUS_CHECK = "STATUS_CHECK"
    """We asked the gateway, server to server."""

    WEBHOOK = "WEBHOOK"
    """The gateway told us in a notification whose signature matched."""


class WebhookOutcome(StrEnum):
    """What applying one verified webhook did to our records."""

    STATUS_CHANGED = "STATUS_CHANGED"
    """The payment attempt moved to a new status."""

    NO_CHANGE = "NO_CHANGE"
    """The report was a repeat, stale or about a final status, so nothing was written."""

    UNKNOWN_ORDER = "UNKNOWN_ORDER"
    """No payment attempt of ours has the order id; nothing changed and the fact is audited."""


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Base of every domain event: the moment the fact happened, as told by the service clock."""

    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentLinkCreated(DomainEvent):
    """The gateway made a payment link for an attempt; the attempt is now LINK_CREATED.

    If a gateway report moved the attempt on during the call, it keeps that status and gains
    only the link details.
    """

    payment_attempt_id: str
    order_id: str
    offer_id: str
    amount_in_paise: int
    gateway_mode: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentLinkCreationFailed(DomainEvent):
    """The create-link call certainly made no link; the attempt is now LINK_CREATION_FAILED.

    A gateway report that moved the attempt on during the call keeps its status instead.
    """

    payment_attempt_id: str
    order_id: str
    offer_id: str
    amount_in_paise: int
    gateway_mode: str
    failure_code: PaymentLinkFailureCode


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentLinkOutcomeUnknown(DomainEvent):
    """The create-link call may have made a link; the attempt is now OUTCOME_UNKNOWN (ADR 0005).

    cause_error_code is the code of the domain error that left the outcome unknown, or
    UNEXPECTED_ERROR for an exception without one. A gateway report that moved the attempt on
    during the call keeps its status instead.
    """

    payment_attempt_id: str
    order_id: str
    offer_id: str
    amount_in_paise: int
    gateway_mode: str
    cause_error_code: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentStatusChanged(DomainEvent):
    """A gateway report moved an attempt to a new status.

    amount_in_paise is the link amount; amount_paid_in_paise is what the gateway reports as paid,
    which a discount can make lower, so the two are recorded side by side and never compared.
    """

    payment_attempt_id: str
    order_id: str
    previous_status: PaymentAttemptStatus
    new_status: PaymentAttemptStatus
    reported_status: GatewayPaymentStatus
    source: StatusReportSource
    amount_in_paise: int
    amount_paid_in_paise: int | None
    gateway_transaction_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class WebhookRejected(DomainEvent):
    """A received webhook was refused before any field was trusted.

    webhook_delivery_id is our own id for this delivery, because nothing in an unverified
    notification may be used; rejection_code is the code of the domain error that refused it.
    """

    webhook_delivery_id: str
    rejection_code: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WebhookProcessed(DomainEvent):
    """A verified webhook was handled with the given outcome, for example an unknown order id."""

    order_id: str
    outcome: WebhookOutcome
    reported_status: GatewayPaymentStatus
    amount_paid_in_paise: int | None
    gateway_transaction_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class OfferQuoteMismatch(DomainEvent):
    """The lender's monthly figure and our schedule differ by more than ₹1 (ADR 0001).

    The offer is still shown with the lender's figure; this event is the evidence of the gap.
    """

    offer_id: str
    tenure_in_months: int
    price_in_paise: int
    quoted_monthly_installment_in_paise: int
    schedule_regular_installment_in_paise: int
    quoted_extra_in_total_in_paise: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SaleStarted(DomainEvent):
    """A merchant started a sale of one product at its counter price; it is now CHOOSING."""

    sale_id: str
    merchant_id: str
    product_id: str
    price_in_paise: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SaleStatusChanged(DomainEvent):
    """A sale moved to a new status; occurred_at is its new status_changed_at.

    chosen_offer_id is set once the customer has agreed to a plan; payment_attempt_id is set
    when a gateway payment report caused the move.
    """

    sale_id: str
    merchant_id: str
    previous_status: SaleStatus
    new_status: SaleStatus
    chosen_offer_id: str | None
    payment_attempt_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SalePaymentOutcomeIgnored(DomainEvent):
    """A payment report reached a sale that was not awaiting payment (CHOOSING or EXPIRED).

    Nothing changed; the event is the evidence that a payment arrived where none was expected.
    """

    sale_id: str
    merchant_id: str
    sale_status: SaleStatus
    payment_outcome: SalePaymentOutcome
    payment_attempt_id: str
