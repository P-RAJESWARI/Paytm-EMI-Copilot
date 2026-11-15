"""Integration: QR exchange, budget, comfort and plans on PostgreSQL with the Mock gateway."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.core.qr_token_signer import hash_qr_token_nonce
from emi_copilot.domain.comfort import ComfortBand
from emi_copilot.domain.errors import (
    CustomerQrTokenInvalidError,
    CustomerSessionTokenInvalidError,
)
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.plan_advice_types import PlanComparison
from tests.fixed_clock import FixedClock
from tests.integration.services.customer_flow_database_wiring import (
    DESIGN_SALE_IDS,
    DatabaseCustomerServices,
    nonce_for,
    wire_database_customer_services,
)
from tests.payment_builders import CREATED_AT
from tests.sale_builders import CHOOSING_LIFETIME, build_qr_token_state
from tests.unit.services.customer.customer_service_wiring import credentials_of, sign_qr_token

pytestmark = pytest.mark.integration

SALE_ID = DESIGN_SALE_IDS[0]
REISSUED_NONCE = "synthetic-nonce-reissued"


@pytest.fixture
def services(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> DatabaseCustomerServices:
    """Stores the design shop and its sales, then wires the customer services."""
    return wire_database_customer_services(session_factory, fixed_clock)


def exchange(services: DatabaseCustomerServices, sale_id: str = SALE_ID) -> str:
    """Signs the sale's stored QR token; the caller exchanges it."""
    return sign_qr_token(services.qr_token_signer, nonce=nonce_for(sale_id), sale_id=sale_id)


def start(services: DatabaseCustomerServices) -> CustomerSessionCredentials:
    """Exchanges the first sale's QR and gives the phone's credentials."""
    return credentials_of(services.sessions.start(exchange(services)))


def offer_ids_and_ratios(comparison: PlanComparison) -> list[tuple[str, int | None]]:
    """Lists each plan's offer id and comfort ratio in basis points, in C4 order."""
    return [
        (
            plan.ranked_plan.priced_offer.offer.offer_id,
            None if plan.comfort is None else plan.comfort.total_ratio.in_basis_points,
        )
        for plan in comparison.advised_plans
    ]


def test_exchange_stores_the_exchange_and_a_reuse_is_refused(
    services: DatabaseCustomerServices,
) -> None:
    """The exchange moment is stored on the sale; the same QR then opens nothing."""
    qr_token = exchange(services)
    started_session = services.sessions.start(qr_token)
    stored_sale = services.read_sale(SALE_ID)
    assert stored_sale is not None
    assert stored_sale.qr_token.exchanged_at == CREATED_AT
    assert started_session.session_code == "4821"
    assert started_session.shop_name == "Ravi Electronics"
    with pytest.raises(CustomerQrTokenInvalidError):
        services.sessions.start(qr_token)


def test_exchange_with_the_wrong_nonce_is_refused(services: DatabaseCustomerServices) -> None:
    """A token for this sale but with another sale's nonce opens nothing."""
    with pytest.raises(CustomerQrTokenInvalidError):
        services.sessions.start(
            sign_qr_token(
                services.qr_token_signer, nonce=nonce_for(DESIGN_SALE_IDS[1]), sale_id=SALE_ID
            )
        )
    stored_sale = services.read_sale(SALE_ID)
    assert stored_sale is not None
    assert stored_sale.qr_token.exchanged_at is None


def test_exchange_on_an_overdue_sale_stores_the_expiry_and_refuses(
    services: DatabaseCustomerServices,
) -> None:
    """The expiry commits even though the exchange is refused."""
    qr_token = sign_qr_token(
        services.qr_token_signer,
        nonce=nonce_for(SALE_ID),
        sale_id=SALE_ID,
        lifetime=CHOOSING_LIFETIME * 2,
    )
    services.clock.advance(CHOOSING_LIFETIME)
    with pytest.raises(CustomerQrTokenInvalidError):
        services.sessions.start(qr_token)
    stored_sale = services.read_sale(SALE_ID)
    assert stored_sale is not None
    assert stored_sale.status is SaleStatus.EXPIRED


def test_exchange_of_a_new_qr_revokes_the_earlier_session(
    services: DatabaseCustomerServices,
) -> None:
    """The merchant's new QR moves the sale to a new phone; the earlier token stops working."""
    first_credentials = start(services)
    with services.unit_of_work_factory() as unit_of_work:
        sale = unit_of_work.sales.find_by_id_for_update(SALE_ID)
        assert sale is not None
        unit_of_work.sales.update(
            sale.issue_qr_token(
                build_qr_token_state(nonce_hash=hash_qr_token_nonce(REISSUED_NONCE))
            )
        )
    second_session = services.sessions.start(
        sign_qr_token(services.qr_token_signer, nonce=REISSUED_NONCE, sale_id=SALE_ID)
    )
    stored_first = services.read_session(first_credentials.customer_session_id)
    assert stored_first is not None
    assert stored_first.revoked_at == CREATED_AT
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.sessions.resolve(first_credentials)
    assert services.sessions.resolve(credentials_of(second_session)).id == (
        second_session.customer_session_id
    )


def test_budget_and_plans_reach_the_funnel_once_each_with_the_first_budget(
    services: DatabaseCustomerServices,
) -> None:
    """BUDGET_TOLD (₹3,000) and PLANS_VIEWED are written once per sale, never failing."""
    credentials = start(services)
    services.choices.confirm_budget(credentials, Money.from_rupees(3000))
    services.choices.confirm_budget(credentials, Money.from_rupees(3500))
    services.choices.record_comfort_check_choice(credentials, has_customer_consented=False)
    services.plans.compare_plans(credentials)
    services.plans.compare_plans(credentials)
    funnel_events = services.read_funnel_events(SALE_ID)
    assert [event.stage for event in funnel_events] == [
        FunnelStage.BUDGET_TOLD,
        FunnelStage.PLANS_VIEWED,
    ]
    assert funnel_events[0].monthly_budget == Money.from_rupees(3000)


def test_plans_at_three_thousand_with_comfort_give_the_design_order_and_ratios(
    services: DatabaseCustomerServices,
) -> None:
    """C4: cardless 3,350 bp, then no-cost 3,889 bp, then card 3,950 bp (ADR 0020)."""
    credentials = start(services)
    services.choices.confirm_budget(credentials, Money.from_rupees(3000))
    services.choices.record_comfort_check_choice(credentials, has_customer_consented=True)
    comparison = services.plans.compare_plans(credentials)
    assert offer_ids_and_ratios(comparison) == [
        ("mock-offer-cardless-12m", 3350),
        ("mock-offer-no-cost-6m", 3889),
        ("mock-offer-card-6m", 3950),
    ]
    assert [plan.comfort.band for plan in comparison.advised_plans if plan.comfort] == [
        ComfortBand.COMFORTABLE,
        ComfortBand.STRETCHING,
        ComfortBand.STRETCHING,
    ]


def test_plans_at_eighteen_hundred_list_every_plan_above_budget(
    services: DatabaseCustomerServices,
) -> None:
    """No plan fits ₹1,800: all three are still shown, without bands after a skip."""
    credentials = start(services)
    services.choices.confirm_budget(credentials, Money.from_rupees(1800))
    services.choices.record_comfort_check_choice(credentials, has_customer_consented=False)
    comparison = services.plans.compare_plans(credentials)
    assert offer_ids_and_ratios(comparison) == [
        ("mock-offer-cardless-12m", None),
        ("mock-offer-no-cost-6m", None),
        ("mock-offer-card-6m", None),
    ]
    assert not comparison.ranking.has_any_plan_within_budget


def test_alternatives_quote_the_shops_64_gb_phone_at_its_price(
    services: DatabaseCustomerServices,
) -> None:
    """C6's cheaper model is the catalogue's 64 GB phone: ₹3,000 a month at 3,667 bp."""
    credentials = start(services)
    services.choices.confirm_budget(credentials, Money.from_rupees(3000))
    services.choices.record_comfort_check_choice(credentials, has_customer_consented=True)
    advice = services.plans.suggest_alternatives(credentials, "mock-offer-no-cost-6m")
    cheaper_model = next(
        item for item in advice.advised_alternatives if item.alternative.product_name
    )
    assert cheaper_model.alternative.product_name == "Example phone, 64 GB"
    assert cheaper_model.alternative.priced_offer.quoted_monthly_installment == (
        Money.from_rupees(3000)
    )
    assert cheaper_model.comfort is not None
    assert cheaper_model.comfort.total_ratio.in_basis_points == 3667
