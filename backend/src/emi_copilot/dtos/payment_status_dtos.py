"""Wire schemas of GET /api/v1/payments/{orderId}/status and the public payment status enum."""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated

from pydantic import Field

from emi_copilot.domain.payments import PaymentAttemptStatus
from emi_copilot.dtos.wire_types import CamelCaseResponseModel, PositiveAmountInPaise
from emi_copilot.services.payment_status_service import PaymentStatusView


class PublicPaymentStatus(StrEnum):
    """Where a payment stands, as the UIs see it; decoupled from the stored attempt status.

    The stored statuses may be renamed or split later without breaking the wire contract.
    """

    CREATING_LINK = "CREATING_LINK"
    """The payment link is being created; ask again in a moment."""

    LINK_FAILED = "LINK_FAILED"
    """No link was made; start again with a new Idempotency-Key."""

    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    """The create-link call timed out; nobody knows whether a link exists (ADR 0005)."""

    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    """The link exists and the gateway has no payment on it yet."""

    PAYMENT_PENDING = "PAYMENT_PENDING"
    """A payment was started on the link; the gateway has no final answer yet."""

    PAID = "PAID"
    """The gateway confirmed the payment, server-side."""

    PAYMENT_FAILED = "PAYMENT_FAILED"
    """The payment was attempted and did not go through; the link may still be paid."""


# Explicit, one row per stored status, so a new stored status cannot reach the wire unmapped.
PUBLIC_STATUS_BY_ATTEMPT_STATUS: Mapping[PaymentAttemptStatus, PublicPaymentStatus] = (
    MappingProxyType(
        {
            PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS: PublicPaymentStatus.CREATING_LINK,
            PaymentAttemptStatus.LINK_CREATION_FAILED: PublicPaymentStatus.LINK_FAILED,
            PaymentAttemptStatus.OUTCOME_UNKNOWN: PublicPaymentStatus.OUTCOME_UNKNOWN,
            PaymentAttemptStatus.LINK_CREATED: PublicPaymentStatus.AWAITING_PAYMENT,
            PaymentAttemptStatus.PAYMENT_PENDING: PublicPaymentStatus.PAYMENT_PENDING,
            PaymentAttemptStatus.PAID: PublicPaymentStatus.PAID,
            PaymentAttemptStatus.PAYMENT_FAILED: PublicPaymentStatus.PAYMENT_FAILED,
        }
    )
)


def to_public_payment_status(attempt_status: PaymentAttemptStatus) -> PublicPaymentStatus:
    """Gives the public status of a stored attempt status."""
    return PUBLIC_STATUS_BY_ATTEMPT_STATUS[attempt_status]


class PaymentStatusResponse(CamelCaseResponseModel):
    """Where one payment stands, confirmed with the gateway server-side on this request.

    amountPaidInPaise is set only when the gateway reports the payment as paid; it can be below
    the link amount when a discount applied.
    """

    order_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0A"])]
    status: Annotated[PublicPaymentStatus, Field(examples=[PublicPaymentStatus.PAID])]
    amount_paid_in_paise: Annotated[PositiveAmountInPaise | None, Field(examples=[2_200_000])]

    @classmethod
    def from_view(cls, status_view: PaymentStatusView) -> "PaymentStatusResponse":
        """Converts the service's status view to the wire form."""
        amount_paid = status_view.amount_paid
        return cls(
            order_id=status_view.order_id,
            status=to_public_payment_status(status_view.status),
            amount_paid_in_paise=None if amount_paid is None else amount_paid.to_paise(),
        )
