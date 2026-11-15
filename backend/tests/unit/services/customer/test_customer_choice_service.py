"""CustomerChoiceService: budget (funnel once), comfort consent or skip, language; CHOOSING only."""

import pytest

from emi_copilot.domain.customer_sessions import ComfortCheckStatus, CustomerLanguage
from emi_copilot.domain.errors import (
    BudgetNotConfirmedError,
    ConsentAlreadyGivenError,
    CustomerSessionTokenInvalidError,
    InvalidMonthlyBudgetError,
)
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from tests.sale_builders import SALE_ID, build_no_cost_chosen_plan
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.customer.customer_service_wiring import (
    SALE_DEADLINE_GAP,
    STANDARD_PROFILE,
    CustomerServices,
    credentials_of,
    sign_qr_token,
    start_session_near_the_sale_deadline,
    store_design_shop,
    wire_customer_services,
)

BUDGET = Money.from_rupees(3000)


@pytest.fixture
def services(kit: ServiceTestKit) -> CustomerServices:
    """Stores the design shop and its CHOOSING sale, then wires the customer services."""
    store_design_shop(kit)
    return wire_customer_services(kit)


@pytest.fixture
def credentials(services: CustomerServices) -> CustomerSessionCredentials:
    """Exchanges the sale's QR for a session."""
    return credentials_of(services.sessions.start(sign_qr_token(services.qr_token_signer)))


def funnel_budgets(kit: ServiceTestKit) -> list[tuple[FunnelStage, Money | None]]:
    """Lists the committed funnel rows past STARTED with their budgets."""
    return [(event.stage, event.monthly_budget) for event in kit.database.funnel_events]


def agree_sale(kit: ServiceTestKit) -> None:
    """Moves the stored sale to READY_TO_PAY, as consent or the simulator would."""
    sale = kit.database.sales_by_id[SALE_ID]
    kit.database.sales_by_id[SALE_ID] = sale.agree_to_plan(
        build_no_cost_chosen_plan(), sale.started_at
    )


def test_confirm_budget_stores_it_and_tells_the_funnel_once_with_the_first_budget(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """₹30,000 (misheard) then ₹3,000: the session keeps ₹3,000, BUDGET_TOLD keeps the first."""
    services.choices.confirm_budget(credentials, Money.from_rupees(30000))
    assert services.choices.confirm_budget(credentials, BUDGET) == BUDGET
    stored_session = kit.database.customer_sessions_by_id[credentials.customer_session_id]
    assert stored_session.monthly_budget == BUDGET
    assert funnel_budgets(kit) == [(FunnelStage.BUDGET_TOLD, Money.from_rupees(30000))]


def test_confirm_budget_of_zero_is_refused_before_anything_is_read(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """A budget must be above zero rupees, in whole paise."""
    with pytest.raises(InvalidMonthlyBudgetError):
        services.choices.confirm_budget(credentials, Money.from_paise(0))
    assert kit.database.funnel_events == []


def test_confirm_budget_on_an_overdue_sale_keeps_the_expiry_and_ends_the_session(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """An expired sale is session unavailable (401); its expiry is committed first."""
    late_credentials = start_session_near_the_sale_deadline(services, kit)
    kit.clock.advance(SALE_DEADLINE_GAP)
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.choices.confirm_budget(late_credentials, BUDGET)
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.EXPIRED
    assert funnel_budgets(kit) == []


def test_confirm_budget_after_the_plan_was_agreed_is_a_conflict(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Steps before consent are closed once the sale is READY_TO_PAY."""
    agree_sale(kit)
    with pytest.raises(ConsentAlreadyGivenError):
        services.choices.confirm_budget(credentials, BUDGET)


def test_comfort_check_allowed_reads_the_profile_and_stores_only_the_choice(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """C3 Allow: COMPLETED with the synthetic profile shown; no income is stored."""
    services.choices.confirm_budget(credentials, BUDGET)
    outcome = services.choices.record_comfort_check_choice(credentials, has_customer_consented=True)
    assert outcome.status is ComfortCheckStatus.COMPLETED
    assert outcome.is_synthetic_data is True
    assert outcome.financial_profile == STANDARD_PROFILE
    stored_session = kit.database.customer_sessions_by_id[credentials.customer_session_id]
    assert stored_session.comfort_check_status is ComfortCheckStatus.COMPLETED
    assert services.financial_profile_port.customer_session_ids == [credentials.customer_session_id]


def test_comfort_check_skipped_reads_nothing(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """C3 Skip is always allowed; the profile port is never asked (rule 9)."""
    services.choices.confirm_budget(credentials, BUDGET)
    outcome = services.choices.record_comfort_check_choice(
        credentials, has_customer_consented=False
    )
    assert (outcome.status, outcome.financial_profile) == (ComfortCheckStatus.SKIPPED, None)
    assert services.financial_profile_port.customer_session_ids == []
    stored_session = kit.database.customer_sessions_by_id[credentials.customer_session_id]
    assert stored_session.comfort_check_status is ComfortCheckStatus.SKIPPED


def test_comfort_check_before_the_budget_is_refused(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """C3 follows C2."""
    with pytest.raises(BudgetNotConfirmedError):
        services.choices.record_comfort_check_choice(credentials, has_customer_consented=True)


def test_comfort_check_after_the_plan_was_agreed_is_a_conflict(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Steps before consent are closed once the sale is READY_TO_PAY."""
    services.choices.confirm_budget(credentials, BUDGET)
    agree_sale(kit)
    with pytest.raises(ConsentAlreadyGivenError):
        services.choices.record_comfort_check_choice(credentials, has_customer_consented=True)
    assert services.financial_profile_port.customer_session_ids == []


def test_choose_language_stores_it_on_the_session(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """The C1 language carries across every later screen and into the receipt."""
    assert (
        services.choices.choose_language(credentials, CustomerLanguage.TAMIL)
        is CustomerLanguage.TAMIL
    )
    stored_session = kit.database.customer_sessions_by_id[credentials.customer_session_id]
    assert stored_session.language is CustomerLanguage.TAMIL
