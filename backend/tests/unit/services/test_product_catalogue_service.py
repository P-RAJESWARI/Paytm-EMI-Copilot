"""ProductCatalogueService: one shop's products with offer counts reused from discovery."""

import pytest

from emi_copilot.domain.catalogue import ProductOfferSummary
from emi_copilot.domain.errors import ProductNotFoundError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.domain.money import Money
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.product_catalogue_service import ProductCatalogueService
from tests.merchant_builders import (
    MERCHANT_ID,
    OTHER_MERCHANT_ID,
    PAIRED_AT,
    build_catalogue_product,
)
from tests.unit.services.conftest import ServiceTestKit

PRINCIPAL = MerchantPrincipal(
    merchant_id=MERCHANT_ID,
    shop_code="SHOP-0001",
    shop_name="Synthetic Electronics",
    device_pairing_id="01JCPAIRING000000000000001",
    device_label="Counter tablet 1",
    access_expires_at=PAIRED_AT,
)
PHONE = build_catalogue_product()
EARBUDS = build_catalogue_product(
    id="01JCPRODUCT000000000000002",
    name="Example earbuds",
    list_price=Money.from_rupees("2499"),
    gateway_product_id="product-synthetic-2",
)
OTHER_SHOPS_PRODUCT = build_catalogue_product(
    id="01JCPRODUCT000000000000003", merchant_id=OTHER_MERCHANT_ID
)


@pytest.fixture
def service(kit: ServiceTestKit) -> ProductCatalogueService:
    """Stores two products of the shop and one of another shop; offers come from the fake."""
    for product in (PHONE, EARBUDS, OTHER_SHOPS_PRODUCT):
        kit.database.products_by_id[product.id] = product
    offer_discovery_service = OfferDiscoveryService(
        kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.event_bus
    )
    return ProductCatalogueService(kit.unit_of_work_factory, offer_discovery_service)


def test_list_products_gives_the_shops_products_by_name_with_offer_counts(
    service: ProductCatalogueService,
) -> None:
    """Design plans A and B are quoted: two plans, one with no extra cost, per product."""
    listed_products = service.list_products(PRINCIPAL)
    assert [listed.product for listed in listed_products] == [EARBUDS, PHONE]
    assert {listed.offer_summary for listed in listed_products} == {
        ProductOfferSummary(plan_count=2, no_extra_cost_plan_count=1)
    }


def test_list_products_asks_the_gateway_about_each_product_at_its_list_price(
    service: ProductCatalogueService, kit: ServiceTestKit
) -> None:
    """Discovery runs once per listed product, never for another shop's product."""
    service.list_products(PRINCIPAL)
    assert kit.payment_gateway.discover_offers_calls == [
        EARBUDS.to_offer_discovery_query(),
        PHONE.to_offer_discovery_query(),
    ]


def test_list_products_with_search_keeps_matching_names_only(
    service: ProductCatalogueService, kit: ServiceTestKit
) -> None:
    """A search narrows the list before any gateway call is made."""
    listed_products = service.list_products(PRINCIPAL, "EARBUDS")
    assert [listed.product for listed in listed_products] == [EARBUDS]
    assert len(kit.payment_gateway.discover_offers_calls) == 1


def test_list_products_with_no_offers_counts_zero_plans(
    service: ProductCatalogueService, kit: ServiceTestKit
) -> None:
    """A product the gateway quotes nothing for is still listed, with zero plans."""
    kit.payment_gateway.offers = ()
    listed_products = service.list_products(PRINCIPAL, "phone")
    assert [listed.offer_summary for listed in listed_products] == [
        ProductOfferSummary(plan_count=0, no_extra_cost_plan_count=0)
    ]


def test_get_product_gives_the_shops_own_product(service: ProductCatalogueService) -> None:
    """A product of the signed-in shop is found by id."""
    assert service.get_product(PRINCIPAL, PHONE.id) == PHONE


@pytest.mark.parametrize("product_id", [OTHER_SHOPS_PRODUCT.id, "01JCPRODUCT000000000000099"])
def test_get_product_of_another_shop_or_unknown_raises_not_found(
    service: ProductCatalogueService, product_id: str
) -> None:
    """Another shop's product looks exactly like one that does not exist."""
    with pytest.raises(ProductNotFoundError):
        service.get_product(PRINCIPAL, product_id)
