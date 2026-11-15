"""SaleAgreementStep: agrees a plan on a locked sale inside the caller's unit of work."""

from dataclasses import dataclass
from datetime import datetime

from emi_copilot.domain.errors import IllegalSaleTransitionError, SaleNotFoundError
from emi_copilot.domain.sales import ChosenPlan, Sale
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork
from emi_copilot.services.sale_expiry import SaleExpiryStep, build_sale_status_changed


@dataclass(frozen=True, slots=True)
class SaleAgreementOutcome:
    """The sale as it now stands, and the refusal to raise once the unit of work has committed.

    On a refusal the sale is the current one (possibly just expired), unchanged by the step.
    """

    sale: Sale
    refusal: IllegalSaleTransitionError | None


class SaleAgreementStep:
    """Locks the sale, expires it if overdue, then moves CHOOSING to READY_TO_PAY with the plan.

    Shared by MarkSaleReadyToPayService (the labelled Mock customer simulator) and customer
    consent (ADR 0022 decision 8), so both move the sale and announce SaleStatusChanged the same
    way. A refusal is returned, not raised, so the caller can let an expiry commit first.
    """

    def __init__(self, event_bus: DomainEventBus, sale_expiry: SaleExpiryStep) -> None:
        """Keeps the bus that announces the move and the step that expires overdue sales."""
        self._event_bus = event_bus
        self._sale_expiry = sale_expiry

    def agree(
        self, unit_of_work: UnitOfWork, sale_id: str, chosen_plan: ChosenPlan, now: datetime
    ) -> SaleAgreementOutcome:
        """Agrees the plan on the locked sale; raises SaleNotFoundError when no sale has the id."""
        locked_sale = unit_of_work.sales.find_by_id_for_update(sale_id)
        if locked_sale is None:
            raise SaleNotFoundError("No sale has this id.")
        current_sale = self._sale_expiry.expire_if_overdue(unit_of_work, locked_sale, now)
        try:
            agreed_sale = current_sale.agree_to_plan(chosen_plan, now)
        except IllegalSaleTransitionError as transition_refusal:
            return SaleAgreementOutcome(sale=current_sale, refusal=transition_refusal)
        unit_of_work.sales.update(agreed_sale)
        self._event_bus.publish(build_sale_status_changed(current_sale, agreed_sale), unit_of_work)
        return SaleAgreementOutcome(sale=agreed_sale, refusal=None)
