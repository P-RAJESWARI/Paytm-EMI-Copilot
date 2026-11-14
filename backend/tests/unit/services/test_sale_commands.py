"""IssueQrTokenService and MarkSaleReadyToPayService: legal only while CHOOSING, expiry kept."""

from datetime import timedelta

import pytest

from emi_copilot.core.qr_token_signer import hash_qr_token_nonce
from emi_copilot.domain.errors import (
    IllegalSaleTransitionError,
    OfferNotFoundError,
    ProductNotFoundError,
    SaleNotFoundError,
)
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType, OfferDiscoveryQuery
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.services.mark_sale_ready_to_pay_service import MarkSaleReadyToPayCommand
from tests.merchant_builders import build_catalogue_product
from tests.payment_builders import CREATED_AT
from tests.sale_builders import (
    SALE_ID,
    SYNTHETIC_NONCE_HASH,
    build_sale,
    build_standard_chosen_plan,
)
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.sale_service_wiring import (
    CHOOSING_LIFETIME,
    OTHER_PRINCIPAL,
    PRINCIPAL,
    SaleServices,
    wire_sale_services,
)

AGREE_TO_PLAN_B = MarkSaleReadyToPayCommand(sale_id=SALE_ID, offer_id="offer-plan-b")


@pytest.fixture
def services(kit: ServiceTestKit) -> SaleServices:
    """Stores the shop's product and a CHOOSING sale of it, then wires the services."""
    product = build_catalogue_product()
    kit.database.products_by_id[product.id] = product
    kit.database.sales_by_id[SALE_ID] = build_sale()
    return wire_sale_services(kit)


def test_issue_qr_token_replaces_the_nonce_hash_so_the_old_token_is_void(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """The new token's nonce hash is stored instead of the old one; the status stays CHOOSING."""
    qr_link = services.issue_qr_token.issue_qr_token(PRINCIPAL, SALE_ID)
    claims = services.qr_token_signer.verify(qr_link.customer_url.split("#t=")[1])
    stored_sale = kit.database.sales_by_id[SALE_ID]
    assert stored_sale.qr_token.nonce_hash == hash_qr_token_nonce(claims.nonce)
    assert stored_sale.qr_token.nonce_hash != SYNTHETIC_NONCE_HASH
    assert stored_sale.status is SaleStatus.CHOOSING
    assert qr_link.expires_at == (CREATED_AT + timedelta(minutes=15)).replace(microsecond=0)


@pytest.mark.parametrize(
    "status", [SaleStatus.READY_TO_PAY, SaleStatus.PAID, SaleStatus.PAYMENT_NOT_COMPLETED]
)
def test_issue_qr_token_after_agreement_raises_a_state_conflict(
    services: SaleServices, kit: ServiceTestKit, status: SaleStatus
) -> None:
    """Once the customer agreed, no new QR code is issued and nothing changes."""
    agreed_sale = build_sale(status=status)
    kit.database.sales_by_id[SALE_ID] = agreed_sale
    with pytest.raises(IllegalSaleTransitionError):
        services.issue_qr_token.issue_qr_token(PRINCIPAL, SALE_ID)
    assert kit.database.sales_by_id[SALE_ID] == agreed_sale


def test_issue_qr_token_for_an_overdue_sale_commits_the_expiry_then_raises(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """The refusal comes after the transaction, so the expiry found on the way is kept."""
    kit.clock.advance(CHOOSING_LIFETIME)
    with pytest.raises(IllegalSaleTransitionError):
        services.issue_qr_token.issue_qr_token(PRINCIPAL, SALE_ID)
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.EXPIRED
    assert kit.audit_event_types() == [AuditEventType.SALE_STATUS_CHANGED]


def test_issue_qr_token_for_another_shops_sale_raises_not_found(services: SaleServices) -> None:
    """Another shop cannot re-issue (or learn of) this sale's QR code."""
    with pytest.raises(SaleNotFoundError):
        services.issue_qr_token.issue_qr_token(OTHER_PRINCIPAL, SALE_ID)


def test_mark_ready_to_pay_freezes_the_requoted_plan_and_records_agreed(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """Plan B is re-quoted at the sale's price and stored exactly as shown."""
    agreed_sale = services.mark_ready_to_pay.mark_ready_to_pay(AGREE_TO_PLAN_B)
    assert agreed_sale.status is SaleStatus.READY_TO_PAY
    assert agreed_sale.chosen_plan == build_standard_chosen_plan()
    assert agreed_sale.status_changed_at == CREATED_AT
    assert kit.database.sales_by_id[SALE_ID] == agreed_sale
    assert [event.stage for event in kit.database.funnel_events] == [FunnelStage.AGREED]
    assert kit.audit_event_types() == [AuditEventType.SALE_STATUS_CHANGED]
    assert kit.last_audit_event().details["chosen_offer_id"] == "offer-plan-b"


def test_mark_ready_to_pay_quotes_the_gateway_at_the_sales_price_not_todays_list_price(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """A later change to the list price does not change the price the sale was started at."""
    product = build_catalogue_product(list_price=Money.from_rupees("25000"))
    kit.database.products_by_id[product.id] = product
    services.mark_ready_to_pay.mark_ready_to_pay(AGREE_TO_PLAN_B)
    assert kit.payment_gateway.discover_offers_calls == [
        OfferDiscoveryQuery(
            price=Money.from_rupees("22000"),
            product_id=product.gateway_product_id,
            brand_id=product.gateway_brand_id,
            category_id=product.gateway_category_id,
        )
    ]


def test_mark_ready_to_pay_with_an_offer_no_longer_quoted_raises_and_changes_nothing(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """Only a plan the gateway still quotes can be agreed to."""
    with pytest.raises(OfferNotFoundError):
        services.mark_ready_to_pay.mark_ready_to_pay(
            MarkSaleReadyToPayCommand(sale_id=SALE_ID, offer_id="offer-plan-z")
        )
    assert kit.database.sales_by_id[SALE_ID] == build_sale()


def test_mark_ready_to_pay_twice_raises_a_state_conflict(services: SaleServices) -> None:
    """The first agreement is the evidence; a second is refused."""
    services.mark_ready_to_pay.mark_ready_to_pay(AGREE_TO_PLAN_B)
    with pytest.raises(IllegalSaleTransitionError):
        services.mark_ready_to_pay.mark_ready_to_pay(AGREE_TO_PLAN_B)


def test_mark_ready_to_pay_for_an_overdue_sale_commits_the_expiry_then_raises(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """A customer agreeing after the hour finds the sale expired, and it stays expired."""
    kit.clock.advance(CHOOSING_LIFETIME + timedelta(seconds=1))
    with pytest.raises(IllegalSaleTransitionError):
        services.mark_ready_to_pay.mark_ready_to_pay(AGREE_TO_PLAN_B)
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.EXPIRED
    assert kit.database.funnel_events == []


def test_mark_ready_to_pay_for_an_unknown_sale_raises_not_found(services: SaleServices) -> None:
    """No gateway call is made for a sale that does not exist."""
    with pytest.raises(SaleNotFoundError):
        services.mark_ready_to_pay.mark_ready_to_pay(
            MarkSaleReadyToPayCommand(sale_id="01JCSALE000000000000000099", offer_id="offer-plan-b")
        )


def test_mark_ready_to_pay_whose_product_is_missing_raises(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """The foreign key rules this out in PostgreSQL; the fake proves the guard."""
    kit.database.products_by_id.clear()
    with pytest.raises(ProductNotFoundError):
        services.mark_ready_to_pay.mark_ready_to_pay(AGREE_TO_PLAN_B)


def test_mark_ready_to_pay_when_the_sale_vanishes_during_the_quote_raises_not_found(
    services: SaleServices, kit: ServiceTestKit
) -> None:
    """The sale is read again, locked, after the gateway call; its absence is not ignored."""

    def remove_every_sale() -> None:
        """Deletes every committed sale while the gateway is being asked for quotes."""
        kit.database.sales_by_id.clear()

    kit.payment_gateway.before_discover_offers = remove_every_sale
    with pytest.raises(SaleNotFoundError):
        services.mark_ready_to_pay.mark_ready_to_pay(AGREE_TO_PLAN_B)
