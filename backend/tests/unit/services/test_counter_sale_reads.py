"""ListCounterSalesService and GetSaleService: today in IST, newest first, overdue sales expired."""

from datetime import UTC, datetime, timedelta

import pytest

from emi_copilot.domain.errors import ProductNotFoundError, SaleNotFoundError
from emi_copilot.domain.payments import AuditEventType
from emi_copilot.domain.sales import Sale, SaleStatus, SessionCode
from tests.merchant_builders import OTHER_MERCHANT_ID, build_catalogue_product
from tests.sale_builders import build_sale
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.sale_service_wiring import (
    CHOOSING_LIFETIME,
    OTHER_PRINCIPAL,
    PRINCIPAL,
    SaleServices,
    wire_sale_services,
)

# 00:15 IST on 15 Nov 2026: the counter day began 15 minutes ago, at 18:30 UTC on 14 Nov.
JUST_AFTER_IST_MIDNIGHT = datetime(2026, 11, 14, 18, 45, tzinfo=UTC)


def store_sale(
    kit: ServiceTestKit, sale_number: int, started_at: datetime, **overrides: object
) -> Sale:
    """Stores a sale with a unique id and code that changed status when it started."""
    sale = build_sale(
        id=f"01JCSALE{sale_number:018d}",
        session_code=SessionCode(f"{sale_number:04d}"),
        started_at=started_at,
        status_changed_at=started_at,
        **overrides,
    )
    kit.database.sales_by_id[sale.id] = sale
    return sale


@pytest.fixture
def services(kit: ServiceTestKit) -> SaleServices:
    """Stores the shop's ₹22,000 product and wires the services at 00:15 IST."""
    product = build_catalogue_product()
    kit.database.products_by_id[product.id] = product
    kit.clock.advance(JUST_AFTER_IST_MIDNIGHT - kit.clock.now())
    return wire_sale_services(kit)


def test_counter_list_keeps_todays_sales_in_ist_newest_first(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """00:01 IST today is in; 23:59 IST yesterday is out, though both are minutes old."""
    yesterday_late = store_sale(kit, 1, datetime(2026, 11, 14, 18, 29, tzinfo=UTC))
    today_first = store_sale(kit, 2, datetime(2026, 11, 14, 18, 31, tzinfo=UTC))
    today_second = store_sale(
        kit, 3, datetime(2026, 11, 14, 18, 40, tzinfo=UTC), status=SaleStatus.READY_TO_PAY
    )
    counter_sales = services.list_counter_sales.list_counter_sales(PRINCIPAL)
    assert [counter_sale.sale for counter_sale in counter_sales] == [today_second, today_first]
    assert {counter_sale.product_name for counter_sale in counter_sales} == {
        "Example phone, 128 GB"
    }
    assert yesterday_late.id in kit.database.sales_by_id


def test_counter_list_leaves_out_expired_sales_and_other_shops(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """An expired sale has left the counter; another shop's sale never appears."""
    store_sale(kit, 1, datetime(2026, 11, 14, 18, 31, tzinfo=UTC), status=SaleStatus.EXPIRED)
    store_sale(
        kit,
        2,
        datetime(2026, 11, 14, 18, 31, tzinfo=UTC),
        merchant_id=OTHER_MERCHANT_ID,
    )
    assert services.list_counter_sales.list_counter_sales(PRINCIPAL) == ()


@pytest.mark.parametrize(
    ("age", "expected_status"),
    [
        (CHOOSING_LIFETIME - timedelta(microseconds=1), SaleStatus.CHOOSING),
        (CHOOSING_LIFETIME, SaleStatus.EXPIRED),
    ],
)
def test_counter_list_expires_a_choosing_sale_at_exactly_3600_seconds(
    services: SaleServices, kit: ServiceTestKit, age: timedelta, expected_status: SaleStatus
) -> None:
    """A microsecond short of an hour the sale is still choosing; at the hour it expires."""
    kit.clock.advance(timedelta(hours=2))
    started_at = kit.clock.now() - age
    store_sale(kit, 1, started_at)
    services.list_counter_sales.list_counter_sales(PRINCIPAL)
    assert kit.database.sales_by_id["01JCSALE000000000000000001"].status is expected_status


def test_counter_list_persists_the_expiry_at_the_deadline_with_its_audit_and_no_funnel_row(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """The expiry is stored, dated at started_at + 1 hour, audited, and left off the list."""
    started_at = datetime(2026, 11, 14, 16, 0, tzinfo=UTC)
    store_sale(kit, 1, started_at)
    agreed = store_sale(kit, 2, started_at, status=SaleStatus.READY_TO_PAY)
    assert services.list_counter_sales.list_counter_sales(PRINCIPAL) == ()
    expired_sale = kit.database.sales_by_id["01JCSALE000000000000000001"]
    assert (expired_sale.status, expired_sale.status_changed_at) == (
        SaleStatus.EXPIRED,
        started_at + CHOOSING_LIFETIME,
    )
    assert kit.database.sales_by_id[agreed.id] == agreed
    assert kit.audit_event_types() == [AuditEventType.SALE_STATUS_CHANGED]
    assert kit.last_audit_event().details["new_status"] == "EXPIRED"
    assert kit.database.funnel_events == []


def test_get_sale_gives_the_shops_sale_with_its_product_name(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """A sale of the signed-in shop is found by id."""
    sale = store_sale(kit, 1, datetime(2026, 11, 14, 18, 31, tzinfo=UTC))
    counter_sale = services.get_sale.get_sale(PRINCIPAL, sale.id)
    assert (counter_sale.sale, counter_sale.product_name) == (sale, "Example phone, 128 GB")


@pytest.mark.parametrize("sale_id", ["01JCSALE000000000000000001", "01JCSALE000000000000000099"])
def test_get_sale_of_another_shop_or_unknown_id_raises_not_found(
    services: SaleServices, kit: ServiceTestKit, sale_id: str
) -> None:
    """Another shop's sale looks exactly like one that does not exist."""
    store_sale(kit, 1, datetime(2026, 11, 14, 18, 31, tzinfo=UTC))
    with pytest.raises(SaleNotFoundError):
        services.get_sale.get_sale(OTHER_PRINCIPAL, sale_id)


def test_get_sale_expires_an_overdue_sale_and_returns_it_expired(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """Reading one sale applies the same expiry rule as the list."""
    sale = store_sale(kit, 1, datetime(2026, 11, 14, 17, 0, tzinfo=UTC))
    assert services.get_sale.get_sale(PRINCIPAL, sale.id).sale.status is SaleStatus.EXPIRED
    assert kit.database.sales_by_id[sale.id].status is SaleStatus.EXPIRED


def test_get_sale_whose_product_is_missing_raises(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """The foreign key rules this out in PostgreSQL; the fake proves the guard."""
    sale = store_sale(kit, 1, datetime(2026, 11, 14, 18, 31, tzinfo=UTC))
    kit.database.products_by_id.clear()
    with pytest.raises(ProductNotFoundError):
        services.get_sale.get_sale(PRINCIPAL, sale.id)
