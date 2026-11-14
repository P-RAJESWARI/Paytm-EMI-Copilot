"""What the gateway says about a payment for one of our order ids, in our own words."""

from dataclasses import dataclass
from enum import StrEnum

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_optional_non_empty_text,
    require_positive_whole_paise_money,
)


class GatewayPaymentStatus(StrEnum):
    """The gateway's view of a payment; adapters map every vendor status to one of these."""

    PAID = "PAID"
    """The customer paid and the gateway confirmed it."""

    PENDING = "PENDING"
    """A payment was started but the gateway has no final answer yet."""

    FAILED = "FAILED"
    """The payment was attempted and did not go through."""

    NOT_FOUND = "NOT_FOUND"
    """The gateway knows no payment for this order id, for example the link was never opened."""


def require_consistent_payment_outcome(
    status: object, gateway_transaction_id: object, amount_paid: object
) -> None:
    """Raises unless the transaction id and the amount paid fit the status.

    A paid outcome has both. Only a paid outcome has an amount paid. An order the gateway does not
    know has no transaction id. Pending and failed outcomes may carry a transaction id.
    """
    if not isinstance(status, GatewayPaymentStatus):
        raise InvalidPaymentGatewayValueError("The status must be a GatewayPaymentStatus.")
    require_optional_non_empty_text(
        gateway_transaction_id, "gateway transaction id", InvalidPaymentGatewayValueError
    )
    if amount_paid is not None:
        require_positive_whole_paise_money(
            amount_paid, "amount paid", InvalidPaymentGatewayValueError
        )
    if status is GatewayPaymentStatus.PAID:
        if gateway_transaction_id is None or amount_paid is None:
            raise InvalidPaymentGatewayValueError(
                "A paid outcome needs a gateway transaction id and the amount paid."
            )
    elif amount_paid is not None:
        raise InvalidPaymentGatewayValueError("Only a paid outcome carries an amount paid.")
    if status is GatewayPaymentStatus.NOT_FOUND and gateway_transaction_id is not None:
        raise InvalidPaymentGatewayValueError("An unknown order has no gateway transaction id.")


# Pattern: Value Object. A status result that exists is internally consistent.
@dataclass(frozen=True, slots=True)
class PaymentStatusResult:
    """The answer to a server-side status check for one order id."""

    order_id: str
    status: GatewayPaymentStatus
    gateway_transaction_id: str | None
    amount_paid: Money | None

    def __post_init__(self) -> None:
        """Rejects a blank order id and a transaction id or amount that does not fit the status."""
        require_non_empty_text(self.order_id, "order id", InvalidPaymentGatewayValueError)
        require_consistent_payment_outcome(
            self.status, self.gateway_transaction_id, self.amount_paid
        )
