"""CustomerPlanService: C4 and C6 on the sale's real product through the audited offer path."""

import pytest

from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.domain.alternatives import AlternativeKind
from emi_copilot.domain.comfort import ComfortBand
from emi_copilot.domain.errors import (
    BudgetNotConfirmedError,
    ConsentAlreadyGivenError,
    CustomerSessionTokenInvalidError,
    PaymentGatewayUnavailableError,
)
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.plan_advice_types import PlanComparison
from tests.merchant_builders import build_catalogue_product
from tests.sale_builders import SALE_ID, build_no_cost_chosen_plan
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.customer.customer_service_wiring import (
    PHONE_64_GB_PRODUCT_ID,
    SALE_DEADLINE_GAP,
    CustomerServices,
    credentials_of,
    sign_qr_token,
    start_session_near_the_sale_deadline,
    store_design_shop,
    wire_customer_services,
)

NO_COST_OFFER_ID = "mock-offer-no-cost-6m"
CARD_OFFER_ID = "mock-offer-card-6m"
CARDLESS_OFFER_ID = "mock-offer-cardless-12m"


@pytest.fixture
def services(kit: ServiceTestKit) -> CustomerServices:
    """Stores the design shop and its CHOOSING sale, then wires the customer services."""
    store_design_shop(kit)
    return wire_customer_services(kit)


@pytest.fixture
def credentials(services: CustomerServices) -> CustomerSessionCredentials:
    """Exchanges the sale's QR for a session."""
    return credentials_of(services.sessions.start(sign_qr_token(services.qr_token_signer)))


def confirm(
    services: CustomerServices,
    credentials: CustomerSessionCredentials,
    budget_in_rupees: int,
    *,
    has_comfort_check: bool = False,
) -> None:
    """Confirms a budget and answers the comfort check."""
    services.choices.confirm_budget(credentials, Money.from_rupees(budget_in_rupees))
    services.choices.record_comfort_check_choice(
        credentials, has_customer_consented=has_comfort_check
    )


def offer_ids(comparison: PlanComparison) -> list[str]:
    """Lists the offer ids in C4 order."""
    return [plan.ranked_plan.priced_offer.offer.offer_id for plan in comparison.advised_plans]


def test_compare_plans_at_three_thousand_gives_the_design_order_without_bands(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """C4 at ₹3,000, comfort skipped: cardless fits, then no-cost, then card; no bands."""
    confirm(services, credentials, 3000)
    comparison = services.plans.compare_plans(credentials)
    assert offer_ids(comparison) == [CARDLESS_OFFER_ID, NO_COST_OFFER_ID, CARD_OFFER_ID]
    assert [
        plan.ranked_plan.budget_fit.amount_above_budget.to_paise()
        for plan in comparison.advised_plans
    ] == [0, 66_667, 85_000]
    assert all(plan.comfort is None for plan in comparison.advised_plans)
    assert kit.payment_gateway.discover_offers_calls == [
        OfferDiscoveryQuery(
            price=Money.from_rupees(22000),
            product_id=MOCK_PHONE_128_GB_PRODUCT_ID,
            brand_id="brand-synthetic",
            category_id="category-synthetic",
        )
    ]


def test_compare_plans_after_comfort_consent_gives_the_design_ratios(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """Design ratios: A 3,889 bp, B 3,950 bp, C 3,350 bp (ADR 0020 decision 4)."""
    confirm(services, credentials, 3000, has_comfort_check=True)
    comparison = services.plans.compare_plans(credentials)
    ratios = {
        plan.ranked_plan.priced_offer.offer.offer_id: (
            plan.comfort.total_ratio.in_basis_points if plan.comfort else None,
            plan.comfort.band if plan.comfort else None,
        )
        for plan in comparison.advised_plans
    }
    assert ratios == {
        NO_COST_OFFER_ID: (3889, ComfortBand.STRETCHING),
        CARD_OFFER_ID: (3950, ComfortBand.STRETCHING),
        CARDLESS_OFFER_ID: (3350, ComfortBand.COMFORTABLE),
    }


def test_compare_plans_when_nothing_fits_still_lists_every_plan(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """₹1,800: every plan is shown, each above the budget; none is hidden."""
    confirm(services, credentials, 1800)
    comparison = services.plans.compare_plans(credentials)
    assert offer_ids(comparison) == [CARDLESS_OFFER_ID, NO_COST_OFFER_ID, CARD_OFFER_ID]
    assert not comparison.ranking.has_any_plan_within_budget


def test_compare_plans_twice_counts_plans_viewed_once(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """The funnel reaches PLANS_VIEWED once per sale, however often the plans are shown."""
    confirm(services, credentials, 3000)
    services.plans.compare_plans(credentials)
    services.plans.compare_plans(credentials)
    assert [event.stage for event in kit.database.funnel_events] == [
        FunnelStage.BUDGET_TOLD,
        FunnelStage.PLANS_VIEWED,
    ]


def test_compare_plans_when_the_gateway_fails_records_no_view(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Plans that were never shown are not counted as viewed."""
    confirm(services, credentials, 3000)

    def fail_discovery() -> None:
        """Stands in for a gateway outage."""
        raise PaymentGatewayUnavailableError("The gateway is unavailable (fake).")

    kit.payment_gateway.before_discover_offers = fail_discovery
    with pytest.raises(PaymentGatewayUnavailableError):
        services.plans.compare_plans(credentials)
    assert FunnelStage.PLANS_VIEWED not in [event.stage for event in kit.database.funnel_events]


def test_compare_plans_when_the_sale_is_agreed_meanwhile_records_no_view_after_agreement(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Consent in another tab during the quote: PLANS_VIEWED never follows AGREED in the funnel."""
    confirm(services, credentials, 3000)
    quote_mock_offers = kit.payment_gateway.before_discover_offers
    assert quote_mock_offers is not None

    def agree_in_another_tab() -> None:
        """Quotes as usual, standing in for the customer consenting meanwhile in another tab."""
        quote_mock_offers()
        sale = kit.database.sales_by_id[SALE_ID]
        kit.database.sales_by_id[SALE_ID] = sale.agree_to_plan(
            build_no_cost_chosen_plan(), sale.started_at
        )

    kit.payment_gateway.before_discover_offers = agree_in_another_tab
    comparison = services.plans.compare_plans(credentials)
    assert offer_ids(comparison) == [CARDLESS_OFFER_ID, NO_COST_OFFER_ID, CARD_OFFER_ID]
    assert [event.stage for event in kit.database.funnel_events] == [FunnelStage.BUDGET_TOLD]


def test_compare_plans_before_the_budget_is_refused(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """C4 needs the confirmed budget."""
    with pytest.raises(BudgetNotConfirmedError):
        services.plans.compare_plans(credentials)


def test_compare_plans_on_an_overdue_sale_keeps_the_expiry_and_ends_the_session(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """The sale's hour ran out: it is stored EXPIRED and the session is unavailable."""
    late_credentials = start_session_near_the_sale_deadline(services, kit)
    confirm(services, late_credentials, 3000)
    kit.clock.advance(SALE_DEADLINE_GAP)
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.plans.compare_plans(late_credentials)
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.EXPIRED


def test_suggest_alternatives_offers_the_dearest_cheaper_model_of_the_same_kind(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """C6: ₹4,000 down and the 64 GB model both give ₹3,000 a month; cardless is the longer one."""
    cheaper_still = build_catalogue_product(
        id="01JCPRODUCT000000000000032",
        name="Example phone, 32 GB",
        list_price=Money.from_rupees(15000),
        gateway_product_id="mock-product-phone-32gb",
    )
    kit.database.products_by_id[cheaper_still.id] = cheaper_still
    confirm(services, credentials, 3000, has_comfort_check=True)
    advice = services.plans.suggest_alternatives(credentials, NO_COST_OFFER_ID)
    by_kind = {item.alternative.kind: item for item in advice.advised_alternatives}
    cheaper_model = by_kind[AlternativeKind.CHEAPER_MODEL]
    assert cheaper_model.alternative.product_id == PHONE_64_GB_PRODUCT_ID
    assert cheaper_model.alternative.priced_offer.quoted_monthly_installment == Money.from_rupees(
        3000
    )
    assert cheaper_model.comfort is not None
    assert cheaper_model.comfort.total_ratio.in_basis_points == 3667
    assert by_kind[AlternativeKind.DOWN_PAYMENT].alternative.down_payment == Money.from_rupees(4000)
    assert by_kind[AlternativeKind.LONGER_TENURE].alternative.priced_offer.offer.offer_id == (
        CARDLESS_OFFER_ID
    )
    assert MOCK_PHONE_64_GB_PRODUCT_ID in [
        query.product_id for query in kit.payment_gateway.discover_offers_calls
    ]


def test_suggest_alternatives_without_a_cheaper_product_offers_no_cheaper_model(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Only the same brand and category count; the earbuds are not a cheaper phone."""
    del kit.database.products_by_id[PHONE_64_GB_PRODUCT_ID]
    confirm(services, credentials, 3000)
    advice = services.plans.suggest_alternatives(credentials, NO_COST_OFFER_ID)
    kinds = [item.alternative.kind for item in advice.advised_alternatives]
    assert AlternativeKind.CHEAPER_MODEL not in kinds
    assert all(item.comfort is None for item in advice.advised_alternatives)


def test_suggest_alternatives_after_the_plan_was_agreed_is_refused(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Once the sale is READY_TO_PAY, C6 is closed and the gateway is not asked."""
    confirm(services, credentials, 3000)
    sale = kit.database.sales_by_id[SALE_ID]
    kit.database.sales_by_id[SALE_ID] = sale.agree_to_plan(
        build_no_cost_chosen_plan(), sale.started_at
    )
    with pytest.raises(ConsentAlreadyGivenError):
        services.plans.suggest_alternatives(credentials, NO_COST_OFFER_ID)
    assert kit.payment_gateway.discover_offers_calls == []
