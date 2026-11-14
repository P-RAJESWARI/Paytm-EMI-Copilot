"""StubCustomerSessionService: sample QR tokens, session tokens, expiry and the budget."""

from dataclasses import replace
from datetime import timedelta

import pytest

from emi_copilot.domain.errors import (
    CustomerQrTokenInvalidError,
    CustomerSessionNotFoundError,
    CustomerSessionTokenInvalidError,
    InvalidMonthlyBudgetError,
)
from emi_copilot.domain.money import Money
from emi_copilot.services.customer_flow.customer_flow_types import (
    ComfortCheckStatus,
    CustomerSessionCredentials,
)
from emi_copilot.services.customer_flow.stub_design_sample import (
    STUB_QR_CODES_BY_TOKEN,
    STUB_RISKY_QR_CODE,
    STUB_STANDARD_QR_CODE,
)
from tests.payment_builders import CREATED_AT
from tests.unit.services.customer_flow.conftest import CustomerFlowKit


def test_start_session_standard_qr_opens_the_design_sample(kit: CustomerFlowKit) -> None:
    """C1: Ravi Electronics, the 128 GB phone at ₹22,000, code 4821, 30 minutes to finish."""
    started_session = kit.services.session_service.start_session(STUB_STANDARD_QR_CODE.qr_token)
    assert started_session.customer_session_id == STUB_STANDARD_QR_CODE.customer_session_id
    assert started_session.session_code == "4821"
    assert started_session.session_token == "01JCTESTID0000000000000001"  # noqa: S105 - test id
    assert started_session.shop_name == "Ravi Electronics"
    assert started_session.product_name == "Example phone, 128 GB"
    assert started_session.price == Money.from_rupees("22000")
    assert started_session.expires_at == CREATED_AT + timedelta(minutes=30)


def test_start_session_risky_qr_gives_the_second_session_code(kit: CustomerFlowKit) -> None:
    """The second sample QR opens its own session with code 4822."""
    started_session = kit.services.session_service.start_session(STUB_RISKY_QR_CODE.qr_token)
    assert started_session.session_code == "4822"
    assert set(STUB_QR_CODES_BY_TOKEN) == {"stub-qr-4821", "stub-qr-4822"}


def test_start_session_unknown_qr_token_raises(kit: CustomerFlowKit) -> None:
    """An unknown QR asks the customer, calmly, for a new one."""
    with pytest.raises(CustomerQrTokenInvalidError, match="ask the shop for a new QR"):
        kit.services.session_service.start_session("stub-qr-0000")


def test_start_session_again_replaces_the_token_and_keeps_progress(kit: CustomerFlowKit) -> None:
    """Re-scanning issues a new token; the old one stops working, the budget is kept."""
    first_credentials = kit.start_standard_session()
    kit.confirm_budget(first_credentials)
    second_credentials = kit.start_standard_session()
    with pytest.raises(CustomerSessionTokenInvalidError):
        kit.services.session_service.confirm_budget(first_credentials, Money.from_rupees("3000"))
    assert second_credentials.session_token != first_credentials.session_token
    summary = kit.services.session_service.get_session_summary(second_credentials)
    assert summary.has_confirmed_budget


def test_start_session_again_gives_a_fresh_lifetime(kit: CustomerFlowKit) -> None:
    """A re-scan 20 minutes in gives another 30 minutes from the re-scan."""
    kit.start_standard_session()
    kit.clock.advance(timedelta(minutes=20))
    started_session = kit.services.session_service.start_session(STUB_STANDARD_QR_CODE.qr_token)
    assert started_session.expires_at == CREATED_AT + timedelta(minutes=50)


def test_valid_token_with_another_session_id_raises_not_found_whether_it_exists_or_not(
    kit: CustomerFlowKit,
) -> None:
    """A token only opens its own session; other ids, real or not, get the same answer."""
    standard_credentials = kit.start_standard_session()
    risky_credentials = kit.start_risky_session()
    for other_session_id in (risky_credentials.customer_session_id, "stub-customer-session-0000"):
        with pytest.raises(CustomerSessionNotFoundError):
            kit.confirm_budget(replace(standard_credentials, customer_session_id=other_session_id))


def test_token_that_opens_no_session_raises_token_invalid(kit: CustomerFlowKit) -> None:
    """An unknown token is a 401 whatever session id it is sent with."""
    with pytest.raises(CustomerSessionTokenInvalidError):
        kit.confirm_budget(CustomerSessionCredentials("stub-customer-session-0000", "stub-token"))


def test_get_session_summary_reports_progress_without_the_token(kit: CustomerFlowKit) -> None:
    """Before anything: no budget, no comfort answer, no consent; then budget and skip."""
    credentials = kit.start_standard_session()
    summary = kit.services.session_service.get_session_summary(credentials)
    assert (summary.has_confirmed_budget, summary.comfort_check_status, summary.has_consented) == (
        False,
        None,
        False,
    )
    assert summary.session_code == "4821"
    assert summary.price == Money.from_rupees("22000")
    assert summary.expires_at == CREATED_AT + timedelta(minutes=30)
    assert not hasattr(summary, "session_token")
    kit.confirm_budget(credentials)
    kit.services.advice_service.run_comfort_check(credentials, has_customer_consented=False)
    summary = kit.services.session_service.get_session_summary(credentials)
    assert summary.has_confirmed_budget
    assert summary.comfort_check_status is ComfortCheckStatus.SKIPPED


def test_get_session_summary_after_consenting_to_the_check_says_completed(
    kit: CustomerFlowKit,
) -> None:
    """Allowing the comfort check shows COMPLETED."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    kit.services.advice_service.run_comfort_check(credentials, has_customer_consented=True)
    summary = kit.services.session_service.get_session_summary(credentials)
    assert summary.comfort_check_status is ComfortCheckStatus.COMPLETED


def test_confirm_budget_with_a_wrong_token_raises(kit: CustomerFlowKit) -> None:
    """A token from another session never opens this one."""
    credentials = kit.start_standard_session()
    with pytest.raises(CustomerSessionTokenInvalidError, match="ask the shop"):
        kit.confirm_budget(replace(credentials, session_token="stub-wrong"))  # noqa: S106 - fake


def test_confirm_budget_after_thirty_minutes_raises_session_ended(kit: CustomerFlowKit) -> None:
    """A session ends 30 minutes after the QR was scanned."""
    credentials = kit.start_standard_session()
    kit.clock.advance(timedelta(minutes=30))
    with pytest.raises(CustomerSessionTokenInvalidError, match="ended"):
        kit.confirm_budget(credentials)


def test_confirm_budget_stores_and_returns_the_budget(kit: CustomerFlowKit) -> None:
    """The confirmed budget is given back as Money."""
    credentials = kit.start_standard_session()
    confirmed_budget = kit.services.session_service.confirm_budget(
        credentials, Money.from_rupees("3000")
    )
    assert confirmed_budget == Money.from_rupees("3000")


def test_confirm_budget_of_zero_raises(kit: CustomerFlowKit) -> None:
    """A zero budget is refused."""
    credentials = kit.start_standard_session()
    with pytest.raises(InvalidMonthlyBudgetError):
        kit.services.session_service.confirm_budget(credentials, Money.from_paise(0))
