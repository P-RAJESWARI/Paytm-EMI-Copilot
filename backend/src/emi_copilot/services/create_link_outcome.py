"""How a create-link call's outcome is saved, described and replayed, for PaymentHandoffService."""

from dataclasses import replace
from datetime import datetime
from typing import TypedDict

from emi_copilot.domain.errors import (
    IdempotencyKeyReusedError,
    PaymentLinkCreationFailedError,
    PaymentLinkCreationInProgressError,
    PaymentLinkOutcomeUnknownError,
)
from emi_copilot.domain.events import PaymentLinkOutcomeUnknown
from emi_copilot.domain.payments import PaymentAttempt, PaymentAttemptStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork
from emi_copilot.services.payment_handoff_types import PaymentLinkHandoff

# Cause code audited when a replay finds an attempt in progress for too long (handoff Q2).
STALE_LINK_CREATION_CAUSE_CODE = "LINK_CREATION_STALE"


def save_create_link_outcome(
    unit_of_work: UnitOfWork, outcome_attempt: PaymentAttempt
) -> PaymentAttempt:
    """Saves the create-link call's outcome unless a gateway report moved the attempt on first.

    Such a report wins, so PAID is never overwritten; a made link only adds its link details.
    """
    locked_attempt = unit_of_work.payment_attempts.find_by_order_id_for_update(
        outcome_attempt.order_id
    )
    # A vanished row is left to update(), which raises PaymentAttemptNotFoundError.
    if (
        locked_attempt is None
        or locked_attempt.status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS
    ):
        return unit_of_work.payment_attempts.update(outcome_attempt)
    if outcome_attempt.payment_link_url is None:
        return locked_attempt
    return unit_of_work.payment_attempts.update(
        replace(
            locked_attempt,
            gateway_link_id=outcome_attempt.gateway_link_id,
            payment_link_url=outcome_attempt.payment_link_url,
        )
    )


class CreateLinkEventFields(TypedDict):
    """The fields every create-link event shares: ids, the amount in paise and the mode."""

    payment_attempt_id: str
    order_id: str
    offer_id: str
    amount_in_paise: int
    gateway_mode: str


def describe_create_link_attempt(attempt: PaymentAttempt) -> CreateLinkEventFields:
    """Gives the shared create-link event fields of one attempt."""
    return {
        "payment_attempt_id": attempt.id,
        "order_id": attempt.order_id,
        "offer_id": attempt.offer_snapshot.offer_id,
        "amount_in_paise": attempt.amount.to_paise(),
        "gateway_mode": attempt.gateway_mode,
    }


def replay_stored_outcome(
    stored_attempt: PaymentAttempt, request_fingerprint: str
) -> PaymentLinkHandoff:
    """Gives the stored link for a repeated key, or raises the typed error of its outcome.

    A different body is IDEMPOTENCY_KEY_REUSED. An attempt without a stored link URL raises
    instead of re-sending: in progress, failed (with its code) or outcome unknown, which also
    covers an attempt a later status report moved on from OUTCOME_UNKNOWN or from in progress.
    """
    if stored_attempt.request_fingerprint != request_fingerprint:
        raise IdempotencyKeyReusedError("The Idempotency-Key was used with a different body.")
    if stored_attempt.status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS:
        raise PaymentLinkCreationInProgressError("The first request with this key is running.")
    # The failure code is set exactly when the attempt is LINK_CREATION_FAILED.
    if stored_attempt.failure_code is not None:
        raise PaymentLinkCreationFailedError(
            stored_attempt.failure_code, "This key's payment link was not created."
        )
    payment_url = stored_attempt.payment_link_url
    if payment_url is None:
        raise PaymentLinkOutcomeUnknownError(
            "This key's payment link call has an unknown outcome; start again with a new key."
        )
    return PaymentLinkHandoff.from_attempt(stored_attempt, payment_url, is_replay=True)


def record_stale_link_creation_as_unknown(
    unit_of_work: UnitOfWork,
    stale_attempt: PaymentAttempt,
    event_bus: DomainEventBus,
    occurred_at: datetime,
) -> PaymentAttempt:
    """Stores a stale in-progress attempt as OUTCOME_UNKNOWN and audits it; never re-sends it.

    The row is locked first: if a gateway report moved the attempt on meanwhile, that newer
    evidence is returned unchanged and nothing is audited.
    """
    # A vanished row is left to update(), which raises PaymentAttemptNotFoundError.
    locked_attempt = (
        unit_of_work.payment_attempts.find_by_order_id_for_update(stale_attempt.order_id)
        or stale_attempt
    )
    if locked_attempt.status is not PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS:
        return locked_attempt
    unknown_attempt = unit_of_work.payment_attempts.update(
        replace(locked_attempt, status=PaymentAttemptStatus.OUTCOME_UNKNOWN)
    )
    event_bus.publish(
        PaymentLinkOutcomeUnknown(
            occurred_at=occurred_at,
            cause_error_code=STALE_LINK_CREATION_CAUSE_CODE,
            **describe_create_link_attempt(locked_attempt),
        ),
        unit_of_work,
    )
    return unknown_attempt
