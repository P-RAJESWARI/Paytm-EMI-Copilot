"""How a create-link call's outcome is saved and described, for PaymentHandoffService."""

from dataclasses import replace
from typing import TypedDict

from emi_copilot.domain.payments import PaymentAttempt, PaymentAttemptStatus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork


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
