"""In-memory PaymentGatewayPort for service tests: scripted answers and a record of every call."""

from collections.abc import Callable
from dataclasses import dataclass, field

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.domain.errors import (
    DomainError,
    InvalidPaymentGatewayValueError,
    WebhookSignatureInvalidError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    EmiOffer,
    EmiType,
    GatewayPaymentStatus,
    OfferDiscoveryQuery,
    PaymentLink,
    PaymentLinkRequest,
    PaymentStatusResult,
    UnverifiedWebhookNotification,
    VerifiedWebhookEvent,
)

FAKE_ADAPTER_NAME = "fake"
FAKE_SIGNATURE_FIELD = "signature"
FAKE_PAYMENT_URL_PREFIX = "https://fake-gateway.invalid/pay/"


def build_design_plan_offers() -> tuple[EmiOffer, ...]:
    """Design plans A and B on ₹22,000 as a lender would quote them, both matching our engine."""
    return (
        EmiOffer(
            offer_id="offer-plan-a",
            lender_label="Brand",
            emi_type=EmiType.NO_COST,
            tenure_in_months=6,
            quoted_monthly_installment=Money.from_rupees("3666.67"),
            quoted_extra_in_total=Money.from_paise(0),
        ),
        EmiOffer(
            offer_id="offer-plan-b",
            lender_label="Your card's bank",
            emi_type=EmiType.STANDARD,
            tenure_in_months=6,
            quoted_monthly_installment=Money.from_rupees("3850.00"),
            quoted_extra_in_total=Money.from_rupees("1100"),
        ),
    )


@dataclass
class FakePaymentGateway(PaymentGatewayPort):
    """A scripted gateway: tests set the offers, errors, statuses and accepted signatures.

    Webhooks are accepted only when their "signature" field names a scripted event, so a test
    controls verification without any cryptography.
    """

    offers: tuple[EmiOffer, ...] = field(default_factory=build_design_plan_offers)
    create_link_error: DomainError | None = None
    status_results_by_order_id: dict[str, PaymentStatusResult] = field(default_factory=dict)
    verified_events_by_signature: dict[str, VerifiedWebhookEvent] = field(default_factory=dict)
    malformed_signatures: set[str] = field(default_factory=set)
    before_discover_offers: Callable[[], None] | None = None
    before_create_link: Callable[[], None] | None = None
    discover_offers_calls: list[OfferDiscoveryQuery] = field(default_factory=list)
    create_link_calls: list[PaymentLinkRequest] = field(default_factory=list)
    status_check_calls: list[str] = field(default_factory=list)

    @property
    def adapter_name(self) -> str:
        """Gives "fake", stored as the gateway mode of attempts this gateway serves."""
        return FAKE_ADAPTER_NAME

    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[EmiOffer, ...]:
        """Records the query, runs the optional hook, then returns the scripted offers."""
        self.discover_offers_calls.append(query)
        if self.before_discover_offers is not None:
            self.before_discover_offers()
        return self.offers

    def create_payment_link(self, request: PaymentLinkRequest) -> PaymentLink:
        """Records the request, runs the hook, then raises the scripted error or makes a link."""
        self.create_link_calls.append(request)
        if self.before_create_link is not None:
            self.before_create_link()
        if self.create_link_error is not None:
            raise self.create_link_error
        return PaymentLink(
            order_id=request.order_id,
            gateway_link_id=f"fake-link-{request.order_id}",
            payment_url=f"{FAKE_PAYMENT_URL_PREFIX}{request.order_id}",
        )

    def get_payment_status(self, order_id: str) -> PaymentStatusResult:
        """Records the check and returns the scripted result, or NOT_FOUND."""
        self.status_check_calls.append(order_id)
        return self.status_results_by_order_id.get(
            order_id,
            PaymentStatusResult(
                order_id=order_id,
                status=GatewayPaymentStatus.NOT_FOUND,
                gateway_transaction_id=None,
                amount_paid=None,
            ),
        )

    def verify_webhook(self, notification: UnverifiedWebhookNotification) -> VerifiedWebhookEvent:
        """Accepts a scripted signature, refuses an unknown one, and fails a malformed one."""
        signature = notification.received_fields.get(FAKE_SIGNATURE_FIELD, "")
        if signature in self.malformed_signatures:
            raise InvalidPaymentGatewayValueError("The signed notification is malformed (fake).")
        verified_event = self.verified_events_by_signature.get(signature)
        if verified_event is None:
            raise WebhookSignatureInvalidError("The notification signature does not match (fake).")
        return verified_event


def build_signed_notification(signature: str) -> UnverifiedWebhookNotification:
    """Builds a notification whose only field is the signature the fake looks up."""
    return UnverifiedWebhookNotification({FAKE_SIGNATURE_FIELD: signature})
