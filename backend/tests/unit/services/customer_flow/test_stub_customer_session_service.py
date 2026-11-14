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
from emi_copilot.services.customer_flow.customer_flow_types import CustomerSessionCredentials
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


def test_start_session_again_replaces_the_token_and_clears_progress(kit: CustomerFlowKit) -> None:
    """Re-scanning restarts the sample; the earlier token no longer opens it."""
    first_credentials = kit.start_standard_session()
    kit.confirm_budget(first_credentials)
    second_credentials = kit.start_standard_session()
    with pytest.raises(CustomerSessionTokenInvalidError):
        kit.services.session_service.confirm_budget(first_credentials, Money.from_rupees("3000"))
    assert second_credentials.session_token != first_credentials.session_token


def test_confirm_budget_for_an_unknown_session_id_raises_not_found(kit: CustomerFlowKit) -> None:
    """A session id nobody started is not found."""
    with pytest.raises(CustomerSessionNotFoundError):
        kit.confirm_budget(CustomerSessionCredentials("stub-customer-session-0000", "stub-token"))


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
