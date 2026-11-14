"""ListCounterSalesService: today's sales at the counter, newest first, for the M2 list."""

from zoneinfo import ZoneInfo

from emi_copilot.core.clock import Clock
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.domain.sales import CounterDay, SaleStatus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.sale_views import CounterSale


class ListCounterSalesService:
    """Lists the shop's sales started in the current local day (IST), leaving out EXPIRED ones.

    Overdue CHOOSING sales are expired first, in the same transaction, so the list never shows a
    sale that has run out of time.
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        sale_expiry: SaleExpiryStep,
        reporting_time_zone: ZoneInfo,
    ) -> None:
        """Keeps the unit-of-work factory, the clock, the expiry step and the shop's time zone."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._sale_expiry = sale_expiry
        self._reporting_time_zone = reporting_time_zone

    def list_counter_sales(self, principal: MerchantPrincipal) -> tuple[CounterSale, ...]:
        """Gives today's non-expired sales of the shop, newest first, each with its product name."""
        now = self._clock.now()
        counter_day = CounterDay.containing(now, self._reporting_time_zone)
        with self._unit_of_work_factory() as unit_of_work:
            self._sale_expiry.expire_overdue_sales_for_merchant(
                unit_of_work, principal.merchant_id, now
            )
            sales = unit_of_work.sales.list_started_between_for_merchant(
                principal.merchant_id,
                counter_day.starts_at,
                counter_day.ends_at,
                SaleStatus.EXPIRED,
            )
            product_names_by_id = {
                product.id: product.name
                for product in unit_of_work.products.list_for_merchant(principal.merchant_id)
            }
        return tuple(
            CounterSale(sale=sale, product_name=product_names_by_id[sale.product_id])
            for sale in sales
        )
