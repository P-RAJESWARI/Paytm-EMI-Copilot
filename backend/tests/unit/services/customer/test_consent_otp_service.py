"""ConsentOtpService: a hashed code per challenge, the resend wait, and the phone kept in memory."""

from dataclasses import replace
from datetime import timedelta

import pytest

from emi_copilot.domain.errors import (
    BudgetNotConfirmedError,
    ConsentAlreadyGivenError,
    CustomerContactUnavailableError,
    OtpResendNotYetAvailableError,
)
from emi_copilot.domain.money import Money
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from tests.fakes.fake_customer_flow_ports import OTP_CODE
from tests.payment_builders import CREATED_AT
from tests.sale_builders import SALE_ID, build_no_cost_chosen_plan
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.customer.customer_service_wiring import (
    OTP_LIFETIME,
    OTP_RESEND_WAIT,
    CustomerServices,
    credentials_of,
    sign_qr_token,
    store_design_shop,
    wire_customer_services,
)


@pytest.fixture
def services(kit: ServiceTestKit) -> CustomerServices:
    """Stores the design shop and its CHOOSING sale, then wires the customer services."""
    store_design_shop(kit)
    return wire_customer_services(kit)


@pytest.fixture
def credentials(services: CustomerServices) -> CustomerSessionCredentials:
    """Exchanges the QR and confirms a ₹3,000 budget."""
    credentials = credentials_of(services.sessions.start(sign_qr_token(services.qr_token_signer)))
    services.choices.confirm_budget(credentials, Money.from_rupees(3000))
    return credentials


def test_request_otp_sends_a_code_and_stores_only_its_keyed_hash(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """C9 shows "ending 42", 5 minutes, resend after 30 seconds, three tries."""
    issued = services.otp.request_otp(credentials)
    assert issued.phone_last_two_digits == "42"
    assert issued.expires_at == CREATED_AT + OTP_LIFETIME
    assert issued.resend_available_at == CREATED_AT + OTP_RESEND_WAIT
    assert issued.attempts_remaining == 3
    (challenge,) = kit.database.otp_challenges_by_id.values()
    assert challenge.code_hash == services.keyed_hasher.hash_consent_otp_code(
        challenge.id, OTP_CODE
    )
    assert services.otp_sender.sent == [("42", OTP_CODE)]


def test_request_otp_again_inside_the_resend_wait_is_refused_with_the_seconds_left(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """A usable code cannot be replaced for 30 seconds (429 with Retry-After)."""
    services.otp.request_otp(credentials)
    kit.clock.advance(timedelta(seconds=10))
    with pytest.raises(OtpResendNotYetAvailableError) as refusal:
        services.otp.request_otp(credentials)
    assert refusal.value.retry_after_in_seconds == 20
    assert len(services.otp_sender.sent) == 1


def test_request_otp_after_the_wait_issues_a_newer_challenge(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """After the wait a new code replaces the old one as the session's latest."""
    services.otp.request_otp(credentials)
    kit.clock.advance(OTP_RESEND_WAIT)
    issued = services.otp.request_otp(credentials)
    assert issued.expires_at == kit.clock.now() + OTP_LIFETIME
    assert len(kit.database.otp_challenges_by_id) == 2


def test_request_otp_after_a_spent_code_issues_one_at_once(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """A code with no attempts left can be replaced without waiting."""
    services.otp.request_otp(credentials)
    (challenge,) = kit.database.otp_challenges_by_id.values()
    kit.database.otp_challenges_by_id[challenge.id] = replace(challenge, attempts_remaining=0)
    services.otp.request_otp(credentials)
    assert len(services.otp_sender.sent) == 2


def test_request_otp_before_the_budget_is_refused_and_sends_nothing(
    services: CustomerServices,
) -> None:
    """C9 follows C2."""
    credentials = credentials_of(services.sessions.start(sign_qr_token(services.qr_token_signer)))
    with pytest.raises(BudgetNotConfirmedError):
        services.otp.request_otp(credentials)
    assert services.otp_sender.sent == []


def test_request_otp_without_a_known_phone_number_is_refused(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """The payment side knows no number: nothing is stored and nothing is sent."""
    services.customer_contact.phone_number = None
    with pytest.raises(CustomerContactUnavailableError):
        services.otp.request_otp(credentials)
    assert kit.database.otp_challenges_by_id == {}
    assert services.otp_sender.sent == []


def test_request_otp_after_the_plan_was_agreed_is_a_conflict(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Once the sale is READY_TO_PAY, no new consent code is sent."""
    sale = kit.database.sales_by_id[SALE_ID]
    kit.database.sales_by_id[SALE_ID] = sale.agree_to_plan(
        build_no_cost_chosen_plan(), sale.started_at
    )
    with pytest.raises(ConsentAlreadyGivenError):
        services.otp.request_otp(credentials)
