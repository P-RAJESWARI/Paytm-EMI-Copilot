"""Webhook notifications from the gateway: untrusted as received, trusted only once verified."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import require_non_empty_text
from emi_copilot.domain.payments.gateway_payment_status import (
    GatewayPaymentStatus,
    require_consistent_payment_outcome,
)


def _freeze_received_fields(received_fields: object) -> Mapping[str, str]:
    """Copies the received fields into a read-only mapping once every key and value is text."""
    if not isinstance(received_fields, Mapping):
        raise InvalidPaymentGatewayValueError("Webhook fields must be a mapping of text to text.")
    for key, value in received_fields.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise InvalidPaymentGatewayValueError(
                "Every webhook field name and value must be text."
            )
    return MappingProxyType(dict(received_fields))


@dataclass(frozen=True, slots=True)
class UnverifiedWebhookNotification:
    """The key/value fields exactly as received on the webhook endpoint. UNTRUSTED.

    Anyone can post to the endpoint, so no field may be read, logged or acted on until the
    gateway port has verified the signature over all of them. The fields are a read-only copy,
    and the repr shows field names only, because values include the signature and may include
    personal data.
    """

    received_fields: Mapping[str, str] = field(hash=False)

    def __post_init__(self) -> None:
        """Freezes a copy of the received fields so nothing can change them before verification."""
        object.__setattr__(self, "received_fields", _freeze_received_fields(self.received_fields))

    def __repr__(self) -> str:
        """Shows the received field names only, never their untrusted or sensitive values."""
        return f"UnverifiedWebhookNotification(field_names={sorted(self.received_fields)!r})"


# Pattern: Value Object. Only the gateway port creates it, and only after a valid signature.
@dataclass(frozen=True, slots=True)
class VerifiedWebhookEvent:
    """A payment update whose signature matched over every received field.

    A webhook always concerns a payment the gateway knows, so NOT_FOUND is never a valid status.
    """

    order_id: str
    status: GatewayPaymentStatus
    gateway_transaction_id: str | None
    amount_paid: Money | None

    def __post_init__(self) -> None:
        """Rejects a blank order id, a NOT_FOUND status and an outcome that does not fit it."""
        require_non_empty_text(self.order_id, "order id", InvalidPaymentGatewayValueError)
        require_consistent_payment_outcome(
            self.status, self.gateway_transaction_id, self.amount_paid
        )
        if self.status is GatewayPaymentStatus.NOT_FOUND:
            raise InvalidPaymentGatewayValueError("A webhook event cannot report NOT_FOUND.")
