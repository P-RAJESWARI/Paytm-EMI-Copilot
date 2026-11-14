"""PaymentStatusService: applies server-side status checks and verified webhooks to attempts."""

from dataclasses import dataclass, replace

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.domain.errors import (
    InvalidPaymentGatewayValueError,
    PaymentAttemptNotFoundError,
    WebhookSignatureInvalidError,
)
from emi_copilot.domain.events import (
    PaymentStatusChanged,
    StatusReportSource,
    WebhookOutcome,
    WebhookProcessed,
    WebhookRejected,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    GatewayPaymentStatus,
    PaymentAttempt,
    PaymentAttemptStatus,
    UnverifiedWebhookNotification,
    VerifiedWebhookEvent,
    find_status_after_gateway_report,
)
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class PaymentStatusView:
    """Where one of our payments stands: order, status, link amount and the amount paid.

    amount_paid is what the gateway reported as paid in this check, if anything. The view holds
    no card or personal data.
    """

    order_id: str
    status: PaymentAttemptStatus
    amount: Money
    amount_paid: Money | None


@dataclass(frozen=True, slots=True)
class WebhookApplication:
    """What one verified webhook did; status is None when the order id is not ours."""

    order_id: str
    outcome: WebhookOutcome
    status: PaymentAttemptStatus | None


@dataclass(frozen=True, slots=True)
class GatewayPaymentReport:
    """One report about a payment, from a status check or a verified webhook."""

    status: GatewayPaymentStatus
    gateway_transaction_id: str | None
    amount_paid: Money | None
    source: StatusReportSource


def _paise_or_none(amount: Money | None) -> int | None:
    """Gives an optional amount in integer paise."""
    return None if amount is None else amount.to_paise()


def _require_attempt(attempt: PaymentAttempt | None, order_id: str) -> PaymentAttempt:
    """Returns the attempt, or raises when none of ours has the order id."""
    if attempt is None:
        raise PaymentAttemptNotFoundError(f"No payment attempt has order id {order_id}.")
    return attempt


class PaymentStatusService:
    """Moves attempts by the transition table, from gateway reports confirmed server-side.

    A client's word is never a status. Each report is applied in one transaction with the row
    locked, and an event is published only when the status really changes, so a repeated or
    stale report writes nothing. A paid amount that differs from the link amount (a discount can
    lower it) is recorded, never refused.
    """

    def __init__(
        self,
        payment_gateway: PaymentGatewayPort,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        id_generator: IdGenerator,
        event_bus: DomainEventBus,
    ) -> None:
        """Keeps the gateway port, unit-of-work factory, clock, id generator and event bus."""
        self._payment_gateway = payment_gateway
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._id_generator = id_generator
        self._event_bus = event_bus

    def get_payment_status(self, order_id: str) -> PaymentStatusView:
        """Asks the gateway about one of our orders, applies the answer and returns the result."""
        with self._unit_of_work_factory() as unit_of_work:
            known_attempt = unit_of_work.payment_attempts.find_by_order_id(order_id)
        _require_attempt(known_attempt, order_id)
        status_result = self._payment_gateway.get_payment_status(order_id)
        report = GatewayPaymentReport(
            status=status_result.status,
            gateway_transaction_id=status_result.gateway_transaction_id,
            amount_paid=status_result.amount_paid,
            source=StatusReportSource.STATUS_CHECK,
        )
        with self._unit_of_work_factory() as unit_of_work:
            locked_attempt = unit_of_work.payment_attempts.find_by_order_id_for_update(order_id)
            current_attempt, _ = self._apply_report(
                unit_of_work, _require_attempt(locked_attempt, order_id), report
            )
        return PaymentStatusView(
            order_id=order_id,
            status=current_attempt.status,
            amount=current_attempt.amount,
            amount_paid=status_result.amount_paid,
        )

    def get_payment_status_for_merchant(self, merchant_id: str, order_id: str) -> PaymentStatusView:
        """Checks the order like get_payment_status, only if it pays for one of the shop's sales.

        Another shop's order, and an order made for no sale, are not found (404), so their
        existence stays hidden and the gateway is never asked about them.
        """
        with self._unit_of_work_factory() as unit_of_work:
            attempt = unit_of_work.payment_attempts.find_by_order_id(order_id)
            is_shops_attempt = (
                attempt is not None
                and attempt.sale_id is not None
                and unit_of_work.sales.find_by_id_for_merchant(merchant_id, attempt.sale_id)
                is not None
            )
        if not is_shops_attempt:
            raise PaymentAttemptNotFoundError(f"No payment of this shop has order id {order_id}.")
        return self.get_payment_status(order_id)

    def apply_webhook(self, notification: UnverifiedWebhookNotification) -> WebhookApplication:
        """Verifies a notification, then applies it idempotently; a refusal is audited, re-raised.

        A malformed notification whose signature matched is refused the same way.
        """
        try:
            verified_event = self._payment_gateway.verify_webhook(notification)
        except (WebhookSignatureInvalidError, InvalidPaymentGatewayValueError) as refusal:
            self._record_webhook_rejected(refusal.code)
            raise
        report = GatewayPaymentReport(
            status=verified_event.status,
            gateway_transaction_id=verified_event.gateway_transaction_id,
            amount_paid=verified_event.amount_paid,
            source=StatusReportSource.WEBHOOK,
        )
        with self._unit_of_work_factory() as unit_of_work:
            attempt = unit_of_work.payment_attempts.find_by_order_id_for_update(
                verified_event.order_id
            )
            if attempt is None:
                return self._record_unknown_order(unit_of_work, verified_event)
            current_attempt, has_changed = self._apply_report(unit_of_work, attempt, report)
        return WebhookApplication(
            order_id=verified_event.order_id,
            outcome=WebhookOutcome.STATUS_CHANGED if has_changed else WebhookOutcome.NO_CHANGE,
            status=current_attempt.status,
        )

    def _apply_report(
        self, unit_of_work: UnitOfWork, attempt: PaymentAttempt, report: GatewayPaymentReport
    ) -> tuple[PaymentAttempt, bool]:
        """Applies the transition table; on a change, saves it and publishes PaymentStatusChanged.

        Returns the attempt as it now stands and whether its status changed.
        """
        new_status = find_status_after_gateway_report(attempt.status, report.status)
        if new_status is attempt.status:
            return attempt, False
        updated_attempt = unit_of_work.payment_attempts.update(
            replace(
                attempt,
                status=new_status,
                gateway_transaction_id=report.gateway_transaction_id
                or attempt.gateway_transaction_id,
            )
        )
        self._event_bus.publish(
            PaymentStatusChanged(
                occurred_at=self._clock.now(),
                payment_attempt_id=attempt.id,
                order_id=attempt.order_id,
                previous_status=attempt.status,
                new_status=new_status,
                reported_status=report.status,
                source=report.source,
                amount_in_paise=attempt.amount.to_paise(),
                amount_paid_in_paise=_paise_or_none(report.amount_paid),
                gateway_transaction_id=report.gateway_transaction_id,
            ),
            unit_of_work,
        )
        return updated_attempt, True

    def _record_unknown_order(
        self, unit_of_work: UnitOfWork, verified_event: VerifiedWebhookEvent
    ) -> WebhookApplication:
        """Audits a verified webhook about an order id that is not ours; nothing else changes."""
        self._event_bus.publish(
            WebhookProcessed(
                occurred_at=self._clock.now(),
                order_id=verified_event.order_id,
                outcome=WebhookOutcome.UNKNOWN_ORDER,
                reported_status=verified_event.status,
                amount_paid_in_paise=_paise_or_none(verified_event.amount_paid),
                gateway_transaction_id=verified_event.gateway_transaction_id,
            ),
            unit_of_work,
        )
        return WebhookApplication(
            order_id=verified_event.order_id, outcome=WebhookOutcome.UNKNOWN_ORDER, status=None
        )

    def _record_webhook_rejected(self, rejection_code: str) -> None:
        """Audits a refused webhook in its own transaction, under a delivery id of our own."""
        with self._unit_of_work_factory() as unit_of_work:
            self._event_bus.publish(
                WebhookRejected(
                    occurred_at=self._clock.now(),
                    webhook_delivery_id=self._id_generator.new_id(),
                    rejection_code=rejection_code,
                ),
                unit_of_work,
            )
