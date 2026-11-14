"""Lifecycle states of one attempt to hand a sale off to the payment gateway."""

from enum import StrEnum


class PaymentAttemptStatus(StrEnum):
    """Where a payment attempt stands; stored by value, so a rename needs a migration.

    OUTCOME_UNKNOWN means the create-link call timed out, so we cannot tell whether the gateway
    made a link; it is never retried silently and a replay asks for a new key (ADR 0005).
    """

    LINK_CREATION_IN_PROGRESS = "LINK_CREATION_IN_PROGRESS"
    LINK_CREATED = "LINK_CREATED"
    LINK_CREATION_FAILED = "LINK_CREATION_FAILED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    PAYMENT_FAILED = "PAYMENT_FAILED"


STATUSES_ENDED_WITHOUT_A_PAYABLE_LINK = frozenset(
    {PaymentAttemptStatus.LINK_CREATION_FAILED, PaymentAttemptStatus.PAYMENT_FAILED}
)
"""Only after an attempt in one of these may its sale take a new link: nothing can be paid.

Every other status may still be paid (in progress, created, pending, outcome unknown) or was
paid, so a second link could let the customer pay twice. The services settle the two that could
otherwise last for ever (a stale in-progress attempt, and an outcome-unknown one the gateway
reports NOT_FOUND once its create call has surely ended); see LatestSaleAttemptCheck.
"""
