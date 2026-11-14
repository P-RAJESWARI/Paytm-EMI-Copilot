"""MockPaymentGatewayAdapter: a labelled, simulated payment gateway; no network and no money."""

import hashlib
import logging
import re
import threading
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import quote_mock_offers
from emi_copilot.adapters.payment_gateway.mock_webhook_signature import (
    MOCK_AMOUNT_IN_PAISE_FIELD,
    MOCK_ORDER_ID_FIELD,
    MOCK_SIGNATURE_FIELD,
    MOCK_STATUS_FIELD,
    MOCK_TRANSACTION_ID_FIELD,
    calculate_mock_webhook_signature,
    require_valid_mock_webhook_signature,
)
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import (
    InvalidMoneyAmountError,
    InvalidPaymentGatewayValueError,
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    EmiOffer,
    GatewayPaymentStatus,
    OfferDiscoveryQuery,
    PaymentLink,
    PaymentLinkRequest,
    PaymentStatusResult,
    UnverifiedWebhookNotification,
    VerifiedWebhookEvent,
)

MOCK_ADAPTER_NAME = "mock"
MOCK_ACTIVE_WARNING = "MockPaymentGatewayAdapter active: payments are simulated, no money moves"
MOCK_PAYMENT_URL_PREFIX = "https://mock-payments.invalid/pay/"
DEFAULT_PAYMENT_COMPLETION_DELAY = timedelta(seconds=30)
# RFC 2104: an HMAC key shorter than the hash output (32 bytes for SHA-256) weakens it.
MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES = 32
_SIMULATABLE_OUTCOMES = frozenset({GatewayPaymentStatus.PAID, GatewayPaymentStatus.FAILED})
# Paise fit in a signed 64-bit integer, which never needs more than 19 digits.
_AMOUNT_IN_PAISE_PATTERN = re.compile(r"[0-9]{1,19}")
_DERIVED_ID_HEX_LENGTH = 20

mock_gateway_logger = logging.getLogger(__name__)


def _derive_mock_id(prefix: str, order_id: str) -> str:
    """Derives a stable, URL-safe id from an order id, so the same order always gets the same id."""
    order_id_digest = hashlib.sha256(order_id.encode("utf-8")).hexdigest()
    return f"{prefix}-{order_id_digest[:_DERIVED_ID_HEX_LENGTH]}"


@dataclass(frozen=True, slots=True)
class _MockPaymentRecord:
    """What the Mock remembers about one order's link: amount, creation time, forced outcome."""

    amount: Money
    created_at: datetime
    simulated_outcome: GatewayPaymentStatus | None = None


# Pattern: Adapter (Mock). Implements PaymentGatewayPort with simulated offers, links, statuses
# and signed webhooks, so the whole payment flow runs locally with no network and no keys.
class MockPaymentGatewayAdapter(PaymentGatewayPort):
    """A simulated gateway, the local-development default; it announces itself when built.

    Demo pricing rule (not any lender's): on price P it always quotes three offers, the design
    plans scaled to P (ADR 0002 labels). A is no-cost over 6 months from "Brand"; B is 6 months
    from "Your card's bank" with an extra of 5% of P; C is 12 months from "Demo cardless lender
    (Mock)" with an extra of P x 2600 / 22000. Extras are rounded half-up to the paisa once; the
    quoted monthly installment is the NoCostStrategy (A) or QuotedTotalStrategy (B, C) regular
    installment. At ₹22,000 that is ₹3,666.67, ₹3,850.00 and ₹2,050.00 a month, with extras of
    ₹0, ₹1,100 and ₹2,600.

    Links are remembered in this instance only (mock-only state, never global): a second link
    for the same order id is refused. A link's payment is PENDING until the completion delay has
    passed on the injected clock, then PAID, unless a test forces an outcome.
    """

    def __init__(
        self,
        clock: Clock,
        webhook_signing_secret: bytes,
        payment_completion_delay: timedelta = DEFAULT_PAYMENT_COMPLETION_DELAY,
    ) -> None:
        """Stores the clock, signing secret and completion delay, then logs that it is a mock."""
        if len(webhook_signing_secret) < MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES:
            raise ValueError(
                "The webhook signing secret must be at least "
                f"{MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES} bytes."
            )
        if payment_completion_delay < timedelta(0):
            raise ValueError("The payment completion delay cannot be negative.")
        self._clock = clock
        self._webhook_signing_secret = webhook_signing_secret
        self._payment_completion_delay = payment_completion_delay
        self._payment_records_by_order_id: dict[str, _MockPaymentRecord] = {}
        self._payment_records_lock = threading.Lock()
        mock_gateway_logger.warning(
            MOCK_ACTIVE_WARNING, extra={"payment_gateway_adapter": MOCK_ADAPTER_NAME}
        )

    @property
    def adapter_name(self) -> str:
        """Gives "mock", the name stored as the gateway mode of every attempt it serves."""
        return MOCK_ADAPTER_NAME

    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[EmiOffer, ...]:
        """Quotes the three demo plans on the query's price; the item ids do not change them."""
        return quote_mock_offers(query.price)

    def create_payment_link(self, request: PaymentLinkRequest) -> PaymentLink:
        """Makes a deterministic link for the order and remembers it; a second one is refused."""
        with self._payment_records_lock:
            if request.order_id in self._payment_records_by_order_id:
                raise PaymentGatewayRequestRejectedError(
                    PaymentGatewayRejectionReason.DUPLICATE_ORDER_ID,
                    "The mock gateway already holds a payment link for this order id.",
                )
            self._payment_records_by_order_id[request.order_id] = _MockPaymentRecord(
                amount=request.amount, created_at=self._clock.now()
            )
        gateway_link_id = _derive_mock_id("mock-link", request.order_id)
        return PaymentLink(
            order_id=request.order_id,
            gateway_link_id=gateway_link_id,
            payment_url=MOCK_PAYMENT_URL_PREFIX + gateway_link_id,
        )

    def get_payment_status(self, order_id: str) -> PaymentStatusResult:
        """Reports NOT_FOUND, PENDING until the delay has passed, then PAID or a forced outcome."""
        with self._payment_records_lock:
            payment_record = self._payment_records_by_order_id.get(order_id)
        if payment_record is None:
            return PaymentStatusResult(
                order_id=order_id,
                status=GatewayPaymentStatus.NOT_FOUND,
                gateway_transaction_id=None,
                amount_paid=None,
            )
        status = self._find_current_status(payment_record)
        return PaymentStatusResult(
            order_id=order_id,
            status=status,
            gateway_transaction_id=(
                None
                if status is GatewayPaymentStatus.PENDING
                else _derive_mock_id("mock-transaction", order_id)
            ),
            amount_paid=payment_record.amount if status is GatewayPaymentStatus.PAID else None,
        )

    def simulate_payment_outcome(self, order_id: str, status: GatewayPaymentStatus) -> None:
        """Mock-only: forces a known order's payment to PAID or FAILED, whatever the clock says."""
        if status not in _SIMULATABLE_OUTCOMES:
            raise InvalidPaymentGatewayValueError("Only PAID or FAILED can be simulated.")
        with self._payment_records_lock:
            payment_record = self._payment_records_by_order_id.get(order_id)
            if payment_record is None:
                raise InvalidPaymentGatewayValueError(
                    "The mock gateway holds no payment link for this order id."
                )
            self._payment_records_by_order_id[order_id] = replace(
                payment_record, simulated_outcome=status
            )

    def verify_webhook(self, notification: UnverifiedWebhookNotification) -> VerifiedWebhookEvent:
        """Checks the HMAC signature over every field first, then reads the event from them.

        A correctly signed notification whose values cannot form an event (an unknown status, a
        non-numeric amount, a PAID event without an amount) raises
        InvalidPaymentGatewayValueError: the sender is genuine but the body is malformed.
        """
        received_fields = notification.received_fields
        require_valid_mock_webhook_signature(received_fields, self._webhook_signing_secret)
        return VerifiedWebhookEvent(
            order_id=received_fields[MOCK_ORDER_ID_FIELD],
            status=_parse_status(received_fields[MOCK_STATUS_FIELD]),
            gateway_transaction_id=received_fields[MOCK_TRANSACTION_ID_FIELD] or None,
            amount_paid=_parse_optional_amount_in_paise(
                received_fields[MOCK_AMOUNT_IN_PAISE_FIELD]
            ),
        )

    def build_signed_notification(
        self,
        order_id: str,
        status: GatewayPaymentStatus,
        transaction_id: str | None,
        amount: Money | None,
    ) -> UnverifiedWebhookNotification:
        """Mock-only: builds a notification this adapter accepts; absent values are empty text."""
        signed_fields = {
            MOCK_ORDER_ID_FIELD: order_id,
            MOCK_STATUS_FIELD: status.value,
            MOCK_TRANSACTION_ID_FIELD: transaction_id or "",
            MOCK_AMOUNT_IN_PAISE_FIELD: "" if amount is None else str(amount.to_paise()),
        }
        signature = calculate_mock_webhook_signature(signed_fields, self._webhook_signing_secret)
        return UnverifiedWebhookNotification(
            received_fields={**signed_fields, MOCK_SIGNATURE_FIELD: signature}
        )

    def _find_current_status(self, payment_record: _MockPaymentRecord) -> GatewayPaymentStatus:
        """Gives the forced outcome if any, else PAID once the completion delay has fully passed."""
        if payment_record.simulated_outcome is not None:
            return payment_record.simulated_outcome
        elapsed_time = self._clock.now() - payment_record.created_at
        if elapsed_time >= self._payment_completion_delay:
            return GatewayPaymentStatus.PAID
        return GatewayPaymentStatus.PENDING


def _parse_status(status_text: str) -> GatewayPaymentStatus:
    """Reads a signed status value; anything outside GatewayPaymentStatus is a malformed body."""
    try:
        return GatewayPaymentStatus(status_text)
    except ValueError as error:
        raise InvalidPaymentGatewayValueError("The notification status is not known.") from error


def _parse_optional_amount_in_paise(amount_text: str) -> Money | None:
    """Reads a signed amount in integer paise; empty text means no amount was paid."""
    if not amount_text:
        return None
    if _AMOUNT_IN_PAISE_PATTERN.fullmatch(amount_text) is None:
        raise InvalidPaymentGatewayValueError("The notification amount must be whole paise.")
    try:
        return Money.from_paise(int(amount_text))
    except InvalidMoneyAmountError as error:
        raise InvalidPaymentGatewayValueError("The notification amount is out of range.") from error
