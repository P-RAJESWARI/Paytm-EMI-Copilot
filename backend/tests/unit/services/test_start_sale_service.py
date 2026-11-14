"""StartSaleService: list price, a free session code, a fresh QR link and Idempotency-Key replay."""

from datetime import timedelta

import pytest

from emi_copilot.core.qr_token_signer import hash_qr_token_nonce
from emi_copilot.domain.errors import (
    IdempotencyKeyReusedError,
    InvalidSaleDataError,
    ProductNotFoundError,
    SessionCodesExhaustedError,
)
from emi_copilot.domain.events import SaleStarted
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType
from emi_copilot.domain.sales import SaleStatus, SessionCode
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork
from emi_copilot.services.sale_views import StartSaleCommand
from tests.merchant_builders import OTHER_MERCHANT_ID, build_catalogue_product
from tests.payment_builders import CREATED_AT
from tests.sale_builders import PRODUCT_ID, build_sale
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.sale_service_wiring import (
    CUSTOMER_WEB_BASE_URL,
    OTHER_PRINCIPAL,
    PRINCIPAL,
    SaleServices,
    wire_sale_services,
)

OTHER_SHOPS_PRODUCT_ID = "01JCPRODUCT000000000000009"


class SimulatedSubscriberFailureError(Exception):
    """Stands in for any subscriber that fails after the sale and its funnel row were written."""


@pytest.fixture
def services(kit: ServiceTestKit) -> SaleServices:
    """Stores the ₹22,000 product of the shop and one of another shop, then wires the services."""
    for product in (
        build_catalogue_product(),
        build_catalogue_product(id=OTHER_SHOPS_PRODUCT_ID, merchant_id=OTHER_MERCHANT_ID),
    ):
        kit.database.products_by_id[product.id] = product
    return wire_sale_services(kit)


def test_start_sale_stores_a_choosing_sale_at_the_list_price_with_a_qr_link(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """The sale is CHOOSING at ₹22,000 with code 0000; its QR link opens the customer app."""
    started_sale = services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID))
    sale = started_sale.counter_sale.sale
    assert (sale.status, sale.price, sale.session_code) == (
        SaleStatus.CHOOSING,
        Money.from_rupees("22000"),
        SessionCode("0000"),
    )
    assert started_sale.counter_sale.product_name == "Example phone, 128 GB"
    assert (sale.started_at, sale.status_changed_at) == (CREATED_AT, CREATED_AT)
    assert started_sale.is_replay is False
    assert kit.database.sales_by_id == {sale.id: sale}


def test_start_sale_qr_link_carries_a_token_in_the_fragment_whose_nonce_hash_is_stored(
    services: SaleServices,
) -> None:
    """Only the nonce hash is stored; the token verifies to this sale and lasts 15 minutes."""
    started_sale = services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID))
    assert started_sale.qr_link is not None
    base_url, token = started_sale.qr_link.customer_url.split("/#t=")
    claims = services.qr_token_signer.verify(token)
    sale = started_sale.counter_sale.sale
    assert base_url == CUSTOMER_WEB_BASE_URL
    assert claims.sale_id == sale.id
    assert sale.qr_token.nonce_hash == hash_qr_token_nonce(claims.nonce)
    assert started_sale.qr_link.expires_at == sale.qr_token.expires_at
    assert sale.qr_token.expires_at == (CREATED_AT + timedelta(minutes=15)).replace(microsecond=0)
    assert "customer_url" not in repr(started_sale.qr_link)


def test_start_sale_commits_the_started_funnel_row_and_audit_with_the_sale(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """One transaction holds the sale, its STARTED row and its SALE_STARTED audit row."""
    started_sale = services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID))
    sale_id = started_sale.counter_sale.sale.id
    assert [(event.sale_id, event.stage) for event in kit.database.funnel_events] == [
        (sale_id, FunnelStage.STARTED)
    ]
    assert kit.audit_event_types() == [AuditEventType.SALE_STARTED]
    assert kit.last_audit_event().details["price_in_paise"] == 2_200_000
    assert kit.database.commit_count == 1


def test_start_sale_leaves_neither_sale_nor_funnel_row_when_a_subscriber_fails(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """A failure after the writes rolls back the sale and its funnel row together."""

    def fail_after_writes(_event: SaleStarted, _unit_of_work: UnitOfWork) -> None:
        """Fails after the audit and funnel subscribers have written their rows."""
        raise SimulatedSubscriberFailureError

    kit.event_bus.subscribe(SaleStarted, fail_after_writes)
    with pytest.raises(SimulatedSubscriberFailureError):
        services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID))
    assert kit.database.sales_by_id == {}
    assert kit.database.funnel_events == []
    assert kit.database.audit_events == []


def test_start_sale_picks_a_code_no_open_sale_of_the_shop_shows(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """An open sale's code is taken; a paid sale's code and another shop's codes are free."""
    for stored_sale in (
        build_sale(id="01JCSALE000000000000000101", session_code=SessionCode("0000")),
        build_sale(
            id="01JCSALE000000000000000102",
            session_code=SessionCode("0001"),
            status=SaleStatus.PAID,
        ),
        build_sale(
            id="01JCSALE000000000000000103",
            session_code=SessionCode("0002"),
            merchant_id=OTHER_MERCHANT_ID,
        ),
    ):
        kit.database.sales_by_id[stored_sale.id] = stored_sale
    started_sale = services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID))
    assert started_sale.counter_sale.sale.session_code == SessionCode("0001")
    assert services.session_code_generator.taken_codes_seen == [frozenset({"0000"})]


def test_start_sale_when_every_code_is_taken_raises_and_stores_nothing(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """Ten thousand open sales in one shop is a conflict, answered calmly with 409."""
    services.session_code_generator.is_exhausted = True
    with pytest.raises(SessionCodesExhaustedError):
        services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID))
    assert kit.database.sales_by_id == {}


@pytest.mark.parametrize("product_id", [OTHER_SHOPS_PRODUCT_ID, "01JCPRODUCT000000000000099"])
def test_start_sale_of_another_shops_or_unknown_product_raises_not_found(
    services: SaleServices, kit: ServiceTestKit, product_id: str
) -> None:
    """Another shop's product looks exactly like one that does not exist."""
    with pytest.raises(ProductNotFoundError):
        services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(product_id))
    assert kit.database.sales_by_id == {}
    assert kit.database.rollback_count == 1


def test_same_key_and_body_replays_the_stored_sale_without_a_qr_link(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """A retried request returns the first sale; no second sale, row or audit is written."""
    command = StartSaleCommand(PRODUCT_ID, idempotency_key="sale-key-0001")
    first_start = services.start_sale.start_sale(PRINCIPAL, command)
    replayed_start = services.start_sale.start_sale(PRINCIPAL, command)
    assert replayed_start.counter_sale == first_start.counter_sale
    assert (replayed_start.is_replay, replayed_start.qr_link) == (True, None)
    assert len(kit.database.sales_by_id) == 1
    assert kit.audit_event_types() == [AuditEventType.SALE_STARTED]


def test_same_key_with_another_body_raises_idempotency_key_reused(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """A key names one request; reusing it for another product is refused (422)."""
    kit.database.products_by_id["01JCPRODUCT000000000000002"] = build_catalogue_product(
        id="01JCPRODUCT000000000000002", name="Example earbuds"
    )
    services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID, "sale-key-0001"))
    with pytest.raises(IdempotencyKeyReusedError):
        services.start_sale.start_sale(
            PRINCIPAL, StartSaleCommand("01JCPRODUCT000000000000002", "sale-key-0001")
        )
    assert len(kit.database.sales_by_id) == 1


def test_keys_are_scoped_to_one_shop(services: SaleServices, kit: ServiceTestKit) -> None:
    """Another shop using the same key starts its own sale."""
    services.start_sale.start_sale(PRINCIPAL, StartSaleCommand(PRODUCT_ID, "sale-key-0001"))
    other_start = services.start_sale.start_sale(
        OTHER_PRINCIPAL, StartSaleCommand(OTHER_SHOPS_PRODUCT_ID, "sale-key-0001")
    )
    assert other_start.is_replay is False
    assert len(kit.database.sales_by_id) == 2


def test_replay_of_an_overdue_sale_gives_it_expired(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """A replay shows the sale as it stands now, after the choosing hour ran out."""
    command = StartSaleCommand(PRODUCT_ID, "sale-key-0001")
    services.start_sale.start_sale(PRINCIPAL, command)
    kit.clock.advance(timedelta(hours=1))
    replayed_start = services.start_sale.start_sale(PRINCIPAL, command)
    assert replayed_start.counter_sale.sale.status is SaleStatus.EXPIRED


@pytest.mark.parametrize(
    ("product_id", "idempotency_key"), [(" ", None), (PRODUCT_ID, " "), (PRODUCT_ID, "k" * 256)]
)
def test_start_sale_command_refuses_a_blank_product_or_a_bad_key(
    product_id: str, idempotency_key: str | None
) -> None:
    """The product id is required; a key is 1 to 255 characters."""
    with pytest.raises(InvalidSaleDataError):
        StartSaleCommand(product_id, idempotency_key)


def test_request_fingerprint_depends_on_the_body_only() -> None:
    """The key is not part of the body; the product id is."""
    assert (
        StartSaleCommand(PRODUCT_ID, "key-1").calculate_request_fingerprint()
        == StartSaleCommand(PRODUCT_ID, "key-2").calculate_request_fingerprint()
    )
    assert (
        StartSaleCommand(PRODUCT_ID).calculate_request_fingerprint()
        != StartSaleCommand("01JCPRODUCT000000000000002").calculate_request_fingerprint()
    )
