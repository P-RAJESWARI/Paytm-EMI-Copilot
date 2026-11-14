"""FunnelEventRecorder: records the funnel stages a sale reaches, as live code learns of them."""

from datetime import datetime

from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.domain.events import SaleStarted, SaleStatusChanged
from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork


def find_stage_reached(event: SaleStatusChanged) -> FunnelStage | None:
    """Gives the stage a status change reaches: AGREED on the first agreement, PAID on payment.

    A retried payment (PAYMENT_NOT_COMPLETED to READY_TO_PAY) is not a second agreement, and
    every other change, such as expiry, reaches no stage.
    """
    if event.new_status is SaleStatus.PAID:
        return FunnelStage.PAID
    if event.previous_status is SaleStatus.CHOOSING and event.new_status is SaleStatus.READY_TO_PAY:
        return FunnelStage.AGREED
    return None


# Pattern: Observer. Sale services announce what happened; the funnel is written here, so no
# service knows the report exists.
class FunnelEventRecorder:
    """Appends STARTED, AGREED and PAID rows in the publisher's unit of work.

    The row commits with the sale change or not at all, because the bus delivers inside that
    transaction. BUDGET_TOLD and PLANS_VIEWED come from the Layer 3 customer flow.
    """

    def __init__(self, id_generator: IdGenerator) -> None:
        """Keeps the generator of funnel event ids."""
        self._id_generator = id_generator

    def subscribe_to(self, event_bus: DomainEventBus) -> None:
        """Listens for sales starting and changing status."""
        event_bus.subscribe(SaleStarted, self.record_sale_started)
        event_bus.subscribe(SaleStatusChanged, self.record_sale_status_changed)

    def record_sale_started(self, event: SaleStarted, unit_of_work: UnitOfWork) -> None:
        """Records that the sale reached STARTED."""
        self._append(
            unit_of_work, event.sale_id, event.merchant_id, FunnelStage.STARTED, event.occurred_at
        )

    def record_sale_status_changed(
        self, event: SaleStatusChanged, unit_of_work: UnitOfWork
    ) -> None:
        """Records AGREED or PAID when the change reaches one; other changes record nothing."""
        stage = find_stage_reached(event)
        if stage is not None:
            self._append(unit_of_work, event.sale_id, event.merchant_id, stage, event.occurred_at)

    def _append(
        self,
        unit_of_work: UnitOfWork,
        sale_id: str,
        merchant_id: str,
        stage: FunnelStage,
        occurred_at: datetime,
    ) -> None:
        """Appends one funnel row for the sale and stage at the event's moment."""
        unit_of_work.funnel_events.append(
            FunnelEvent(
                id=self._id_generator.new_id(),
                sale_id=sale_id,
                merchant_id=merchant_id,
                stage=stage,
                occurred_at=occurred_at,
            )
        )
