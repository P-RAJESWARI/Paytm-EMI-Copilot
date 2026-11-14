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
