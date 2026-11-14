"""SalePaymentLinkIntent: the sale's own rules inside one PaymentHandoffService hand-off."""

from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import ChosenPlanNoLongerOfferedError, SaleNotFoundError
from emi_copilot.domain.events import SaleStatusChanged
from emi_copilot.domain.payments import PaymentAttempt, PricedEmiOffer
from emi_copilot.domain.sales import ChosenPlan, Sale, SaleStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork
from emi_copilot.services.sale_expiry import SALE_NOT_FOUND_DETAIL


class SalePaymentLinkIntent:
    """Makes a hand-off pay for one agreed sale (a PaymentLinkIntent).

    The fresh quote must equal the agreed ChosenPlan exactly (offer, kind, lender, tenure,
    monthly, extra and total), else CHOSEN_PLAN_NO_LONGER_OFFERED. Inside the transaction that
    stores the attempt, the sale is locked: READY_TO_PAY goes ahead, PAYMENT_NOT_COMPLETED is
    first moved back to READY_TO_PAY (RETRY_PAYMENT), and any other status is a 409 conflict.
    """

    def __init__(
        self, sale: Sale, chosen_plan: ChosenPlan, clock: Clock, event_bus: DomainEventBus
    ) -> None:
        """Keeps the sale as read before the quote, its agreed plan, the clock and the bus."""
        self._sale = sale
        self._chosen_plan = chosen_plan
        self._clock = clock
        self._event_bus = event_bus

    def check_quoted_offer(self, priced_offer: PricedEmiOffer | None) -> None:
        """Refuses the link unless the gateway still quotes the agreed plan exactly as shown."""
        if priced_offer is None or ChosenPlan.from_priced_offer(priced_offer) != self._chosen_plan:
            raise ChosenPlanNoLongerOfferedError(
                "The gateway no longer quotes the agreed plan with the figures that were shown."
            )

    def record_intent(self, unit_of_work: UnitOfWork, new_attempt: PaymentAttempt) -> None:
        """Locks the sale and retries a not-completed payment, in the attempt's transaction."""
        locked_sale = unit_of_work.sales.find_by_id_for_merchant_for_update(
            self._sale.merchant_id, self._sale.id
        )
        if locked_sale is None:
            raise SaleNotFoundError(SALE_NOT_FOUND_DETAIL)
        if locked_sale.status is SaleStatus.READY_TO_PAY:
            return
        retried_sale = unit_of_work.sales.update(locked_sale.retry_payment(self._clock.now()))
        self._event_bus.publish(
            SaleStatusChanged(
                occurred_at=retried_sale.status_changed_at,
                sale_id=retried_sale.id,
                merchant_id=retried_sale.merchant_id,
                previous_status=locked_sale.status,
                new_status=retried_sale.status,
                chosen_offer_id=self._chosen_plan.offer_id,
                payment_attempt_id=new_attempt.id,
            ),
            unit_of_work,
        )
