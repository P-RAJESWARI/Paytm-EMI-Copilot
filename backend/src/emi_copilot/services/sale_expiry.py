"""SaleExpiryStep: turns CHOOSING sales past their deadline into EXPIRED ones, deterministically."""

from datetime import datetime, timedelta

from emi_copilot.domain.errors import SaleNotFoundError
from emi_copilot.domain.events import SaleStatusChanged
from emi_copilot.domain.sales import Sale
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork

SALE_NOT_FOUND_DETAIL = "No sale with this id belongs to the shop."


def build_sale_status_changed(previous_sale: Sale, updated_sale: Sale) -> SaleStatusChanged:
    """Describes a command's status change, at the moment the updated sale records."""
    return SaleStatusChanged(
        occurred_at=updated_sale.status_changed_at,
        sale_id=updated_sale.id,
        merchant_id=updated_sale.merchant_id,
        previous_status=previous_sale.status,
        new_status=updated_sale.status,
        chosen_offer_id=(
            None if updated_sale.chosen_plan is None else updated_sale.chosen_plan.offer_id
        ),
        payment_attempt_id=None,
    )


class SaleExpiryStep:
    """Expires overdue CHOOSING sales inside the caller's unit of work, before it reads or acts.

    Why a step and not a derived status or a timer: EXPIRED is stored (with its event, audit row
    and moment), so reports and the live feed see one truth; and running it on every counter
    read and every sale command, with the injected Clock, needs no scheduler process and is
    deterministic in tests. A sale nobody looks at stays CHOOSING in the table until the next
    look, but it is expired at its deadline (started_at + the choosing lifetime), not at the
    moment of that look, so its status_changed_at is exact either way.
    """

    def __init__(self, event_bus: DomainEventBus, choosing_lifetime: timedelta) -> None:
        """Keeps the bus that announces expiries and how long a sale may stay CHOOSING."""
        self._event_bus = event_bus
        self._choosing_lifetime = choosing_lifetime

    def expire_overdue_sales_for_merchant(
        self, unit_of_work: UnitOfWork, merchant_id: str, now: datetime
    ) -> None:
        """Expires every one of the merchant's CHOOSING sales whose deadline has passed."""
        overdue_sales = unit_of_work.sales.list_choosing_started_by_for_merchant_for_update(
            merchant_id, now - self._choosing_lifetime
        )
        for overdue_sale in overdue_sales:
            self.expire_if_overdue(unit_of_work, overdue_sale, now)

    def expire_if_overdue(self, unit_of_work: UnitOfWork, sale: Sale, now: datetime) -> Sale:
        """Expires one locked sale if it is overdue and gives the sale as it now stands."""
        if not sale.is_choosing_overdue(now, self._choosing_lifetime):
            return sale
        expired_sale = unit_of_work.sales.update(
            sale.expire(sale.started_at + self._choosing_lifetime)
        )
        self._event_bus.publish(build_sale_status_changed(sale, expired_sale), unit_of_work)
        return expired_sale

    def load_current_sale_for_update(
        self, unit_of_work: UnitOfWork, merchant_id: str, sale_id: str, now: datetime
    ) -> Sale:
        """Gives the merchant's sale, locked and expired if overdue; another shop's is not found."""
        sale = unit_of_work.sales.find_by_id_for_merchant_for_update(merchant_id, sale_id)
        if sale is None:
            raise SaleNotFoundError(SALE_NOT_FOUND_DETAIL)
        return self.expire_if_overdue(unit_of_work, sale, now)
