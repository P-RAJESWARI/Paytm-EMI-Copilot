"""ProductCatalogueService: the signed-in merchant's products, each with its offer counts."""

from dataclasses import dataclass

from emi_copilot.domain.catalogue import (
    CatalogueProduct,
    ProductOfferSummary,
    summarise_priced_offers,
)
from emi_copilot.domain.errors import ProductNotFoundError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService


@dataclass(frozen=True, slots=True)
class CatalogueProductWithOffers:
    """One product beside the counts of the EMI plans the gateway quotes for it now."""

    product: CatalogueProduct
    offer_summary: ProductOfferSummary


class ProductCatalogueService:
    """Lists and finds products for the principal's shop only; offers come from discovery.

    The offer counts reuse OfferDiscoveryService, so the same gateway quotes, our schedule and
    the quote-mismatch audit stand behind them; no EMI maths is repeated here. A gateway error
    on any product fails the whole list, as partial discovery does (ADR 0011).
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        offer_discovery_service: OfferDiscoveryService,
    ) -> None:
        """Keeps the unit-of-work factory and the offer discovery service."""
        self._unit_of_work_factory = unit_of_work_factory
        self._offer_discovery_service = offer_discovery_service

    def list_products(
        self, principal: MerchantPrincipal, name_search_text: str | None = None
    ) -> tuple[CatalogueProductWithOffers, ...]:
        """Lists the shop's products by name, each with its offer counts; gateway errors propagate.

        The products are read and the transaction closed before any gateway call is made.
        """
        with self._unit_of_work_factory() as unit_of_work:
            products = unit_of_work.products.list_for_merchant(
                principal.merchant_id, name_search_text
            )
        return tuple(
            CatalogueProductWithOffers(
                product=product,
                offer_summary=summarise_priced_offers(
                    self._offer_discovery_service.discover_offers(
                        product.to_offer_discovery_query()
                    )
                ),
            )
            for product in products
        )

    def get_product(self, principal: MerchantPrincipal, product_id: str) -> CatalogueProduct:
        """Gives one of the shop's products; another shop's or an unknown id raises not found."""
        with self._unit_of_work_factory() as unit_of_work:
            product = unit_of_work.products.find_by_id_for_merchant(
                principal.merchant_id, product_id
            )
        if product is None:
            raise ProductNotFoundError("No product with this id is in the shop's catalogue.")
        return product
