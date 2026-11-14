"""SalePaymentOutcomeSubscriber: moves a sale when the gateway reports on its payment attempt."""

from collections.abc import Mapping
from types import MappingProxyType

from emi_copilot.domain.errors import PaymentAttemptNotFoundError, SaleNotFoundError
from emi_copilot.domain.events import (
    PaymentStatusChanged,
    SalePaymentOutcomeIgnored,
    SalePaymentOutcomeIgnoredReason,
    SaleStatusChanged,
)
from emi_copilot.domain.payments import PaymentAttemptStatus
from emi_copilot.domain.sales import PaymentOutcomeEffect, Sale, SalePaymentOutcome
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork

SALE_PAYMENT_OUTCOME_BY_ATTEMPT_STATUS: Mapping[PaymentAttemptStatus, SalePaymentOutcome] = (
    MappingProxyType(
        {
            PaymentAttemptStatus.PAID: SalePaymentOutcome.PAID,
            PaymentAttemptStatus.PAYMENT_FAILED: SalePaymentOutcome.NOT_COMPLETED,
        }
    )
)
"""Attempt statuses that settle a sale's payment; PENDING and link states settle nothing."""


def _describe_status_change(
    sale: Sale, updated_sale: Sale, event: PaymentStatusChanged
) -> SaleStatusChanged:
    """Describes the sale's move caused by the payment report, at the report's moment."""
    return SaleStatusChanged(
        occurred_at=event.occurred_at,
        sale_id=sale.id,
        merchant_id=sale.merchant_id,
        previous_status=sale.status,
        new_status=updated_sale.status,
        chosen_offer_id=None if sale.chosen_plan is None else sale.chosen_plan.offer_id,
        payment_attempt_id=event.payment_attempt_id,
    )


def _is_latest_attempt_of_sale(unit_of_work: UnitOfWork, sale_id: str, attempt_id: str) -> bool:
    """Tells whether the attempt is the sale's newest one, read under the sale's row lock."""
    latest_attempt = unit_of_work.payment_attempts.find_latest_for_sale(sale_id)
    return latest_attempt is not None and latest_attempt.id == attempt_id


# Pattern: Observer. The payment status service knows nothing of sales; this subscriber turns
# a confirmed payment report into the sale's move, in the same transaction.
class SalePaymentOutcomeSubscriber:
    """Applies SaleStateMachine's tolerant payment rules to the sale an attempt pays for.

    Attempts without a sale (Layer 1 callers) are ignored. A report on a sale that was not
    awaiting payment is audited as SalePaymentOutcomeIgnored and never raises, so the gateway
    is not made to resend a webhook that can never apply. A not-completed report applies only
    when its attempt is the sale's latest: on a replaced attempt it would undo the live new
    link, so it is audited as ignored (ATTEMPT_REPLACED). PAID always applies, from any
    attempt: the money was taken, so the sale is paid.
    """

    def __init__(self, event_bus: DomainEventBus) -> None:
        """Keeps the bus it listens on and publishes the sale's own events to."""
        self._event_bus = event_bus

    def subscribe(self) -> None:
        """Listens for payment attempts changing status."""
        self._event_bus.subscribe(PaymentStatusChanged, self.apply_payment_status_change)

    def apply_payment_status_change(
        self, event: PaymentStatusChanged, unit_of_work: UnitOfWork
    ) -> None:
        """Moves the attempt's sale on a PAID or PAYMENT_FAILED report; anything else is skipped."""
        outcome = SALE_PAYMENT_OUTCOME_BY_ATTEMPT_STATUS.get(event.new_status)
        if outcome is None:
            return
        attempt = unit_of_work.payment_attempts.find_by_order_id(event.order_id)
        if attempt is None:
            raise PaymentAttemptNotFoundError(f"No payment attempt has order id {event.order_id}.")
        if attempt.sale_id is None:
            return
        sale = unit_of_work.sales.find_by_id_for_update(attempt.sale_id)
        if sale is None:
            raise SaleNotFoundError(f"The sale {attempt.sale_id} of an attempt is not stored.")
        if outcome is not SalePaymentOutcome.PAID and not _is_latest_attempt_of_sale(
            unit_of_work, sale.id, attempt.id
        ):
            self._publish_ignored(
                unit_of_work, sale, outcome, event, SalePaymentOutcomeIgnoredReason.ATTEMPT_REPLACED
            )
            return
        self._apply_outcome(unit_of_work, sale, outcome, event)

    def _apply_outcome(
        self,
        unit_of_work: UnitOfWork,
        sale: Sale,
        outcome: SalePaymentOutcome,
        event: PaymentStatusChanged,
    ) -> None:
        """Saves and announces a change, audits an ignored report, and skips a repeat."""
        updated_sale, effect = sale.apply_payment_outcome(outcome, event.occurred_at)
        if effect is PaymentOutcomeEffect.STATUS_CHANGED:
            unit_of_work.sales.update(updated_sale)
            self._event_bus.publish(
                _describe_status_change(sale, updated_sale, event), unit_of_work
            )
        elif effect is PaymentOutcomeEffect.IGNORED_NOT_AWAITING_PAYMENT:
            self._publish_ignored(
                unit_of_work,
                sale,
                outcome,
                event,
                SalePaymentOutcomeIgnoredReason.SALE_NOT_AWAITING_PAYMENT,
            )

    def _publish_ignored(
        self,
        unit_of_work: UnitOfWork,
        sale: Sale,
        outcome: SalePaymentOutcome,
        event: PaymentStatusChanged,
        ignored_reason: SalePaymentOutcomeIgnoredReason,
    ) -> None:
        """Announces, for the audit, a report that moved nothing and why."""
        self._event_bus.publish(
            SalePaymentOutcomeIgnored(
                occurred_at=event.occurred_at,
                sale_id=sale.id,
                merchant_id=sale.merchant_id,
                sale_status=sale.status,
                payment_outcome=outcome,
                payment_attempt_id=event.payment_attempt_id,
                ignored_reason=ignored_reason,
            ),
            unit_of_work,
        )
