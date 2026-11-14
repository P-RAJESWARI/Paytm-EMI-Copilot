"""PaymentLink: the link the gateway made, which the customer opens to pay."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.payments.field_validation import require_non_empty_text


def _require_https_url(payment_url: str) -> None:
    """Raises unless the payment URL is an absolute https URL with a host."""
    split_url = urlsplit(payment_url)
    if split_url.scheme != "https" or not split_url.hostname:
        raise InvalidPaymentGatewayValueError("The payment url must be an absolute https URL.")


# Pattern: Value Object. Only a complete https link can be shown to the customer.
@dataclass(frozen=True, slots=True)
class PaymentLink:
    """A link made for our order id: the gateway's own link id and the URL shown to the customer."""

    order_id: str
    gateway_link_id: str
    payment_url: str

    def __post_init__(self) -> None:
        """Rejects blank ids and any payment URL that is not absolute https."""
        require_non_empty_text(self.order_id, "order id", InvalidPaymentGatewayValueError)
        require_non_empty_text(
            self.gateway_link_id, "gateway link id", InvalidPaymentGatewayValueError
        )
        require_non_empty_text(self.payment_url, "payment url", InvalidPaymentGatewayValueError)
        _require_https_url(self.payment_url)
