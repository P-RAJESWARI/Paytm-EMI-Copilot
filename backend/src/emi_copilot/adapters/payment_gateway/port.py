"""PaymentGatewayPort: what services need from a payment gateway, in our domain's words only."""

from abc import ABC, abstractmethod

from emi_copilot.domain.payments import (
    EmiOffer,
    OfferDiscoveryQuery,
    PaymentLink,
    PaymentLinkRequest,
    PaymentStatusResult,
    UnverifiedWebhookNotification,
    VerifiedWebhookEvent,
)


# Pattern: Port and Adapter. Services depend on this interface, so the Mock and the real gateway
# adapter are interchangeable and tests need no network; vendor field names stay in the adapter.
class PaymentGatewayPort(ABC):
    """The payment gateway seen from our side: offers, payment links, status checks, webhooks.

    Every failure leaves an implementation as a typed domain error from domain/errors.py, never as
    a vendor payload, HTTP status or library exception.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Gives the short, stable name of this implementation, such as "mock".

        It is announced in the startup log and stored as payment_attempt.gateway_mode (ADR 0004).
        """

    @abstractmethod
    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[EmiOffer, ...]:
        """Asks the gateway which EMI offers it quotes for the item at the price; may be empty.

        Idempotent read, so an implementation may retry it within its configured limits.

        Raises:
            PaymentGatewayTimeoutError: the gateway did not answer in time.
            PaymentGatewayUnavailableError: the circuit breaker is open or the gateway failed.
            PaymentGatewayRequestRejectedError: the gateway refused the query.
            InvalidPaymentGatewayValueError: the gateway's answer cannot form a valid offer.
        """

    @abstractmethod
    def create_payment_link(self, request: PaymentLinkRequest) -> PaymentLink:
        """Asks the gateway to make a payment link for the order on the chosen plan.

        Never retried, by the implementation or by its caller: a second call could make a second
        link (backend.md section 6, ADR 0005).

        Raises:
            PaymentGatewayTimeoutError: no answer in time, so the outcome is unknown; the gateway
                may have made the link. The attempt is stored as OUTCOME_UNKNOWN (ADR 0005).
            PaymentGatewayUnavailableError: the circuit breaker is open, so nothing was sent, or
                the gateway failed to serve the call.
            PaymentGatewayRequestRejectedError: the gateway refused the request, with a reason.
            InvalidPaymentGatewayValueError: the gateway's answer cannot form a valid link.
        """

    @abstractmethod
    def get_payment_status(self, order_id: str) -> PaymentStatusResult:
        """Asks the gateway, server to server, where the payment for one of our order ids stands.

        Idempotent read, so an implementation may retry it within its configured limits. An
        order the gateway does not know is a NOT_FOUND result, not an error.

        Raises:
            PaymentGatewayTimeoutError: the gateway did not answer in time.
            PaymentGatewayUnavailableError: the circuit breaker is open or the gateway failed.
            PaymentGatewayRequestRejectedError: the gateway refused the status request.
            InvalidPaymentGatewayValueError: the gateway's answer cannot form a valid result.
        """

    @abstractmethod
    def verify_webhook(self, notification: UnverifiedWebhookNotification) -> VerifiedWebhookEvent:
        """Checks the notification's signature over all received fields, then reads the event.

        The signature is checked before any field is trusted or parsed (api-conventions.md
        section 8). No network call is made.

        Raises:
            WebhookSignatureInvalidError: the signature is missing or does not match the fields.
            InvalidPaymentGatewayValueError: the signature matched but the fields cannot form a
                valid event.
        """
