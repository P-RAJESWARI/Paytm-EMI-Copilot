"""GetSaleService: one of the shop's sales, as it stands now."""

from emi_copilot.core.clock import Clock
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.sale_views import CounterSale, build_counter_sale


class GetSaleService:
    """Reads one sale of the signed-in shop; another shop's sale is not found (404).

    An overdue CHOOSING sale is expired and committed before it is returned.
    """

    def __init__(
        self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock, sale_expiry: SaleExpiryStep
    ) -> None:
        """Keeps the unit-of-work factory, the clock and the expiry step."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._sale_expiry = sale_expiry

    def get_sale(self, principal: MerchantPrincipal, sale_id: str) -> CounterSale:
        """Gives the sale with its product name, or raises SaleNotFoundError."""
        with self._unit_of_work_factory() as unit_of_work:
            sale = self._sale_expiry.load_current_sale_for_update(
                unit_of_work, principal.merchant_id, sale_id, self._clock.now()
            )
            return build_counter_sale(unit_of_work, sale)
