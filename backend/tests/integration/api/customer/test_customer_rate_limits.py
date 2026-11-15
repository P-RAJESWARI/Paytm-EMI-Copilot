"""QR exchange, code requests and consent are rate limited (security-and-compliance.md 4)."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.api.customer_dependencies import provide_consent_reference_serial_generator
from emi_copilot.config.settings import ApplicationSettings
from tests.fakes.fake_customer_flow_ports import FixedConsentReferenceSerialGenerator
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import open_api_harness
from tests.integration.api.customer.customer_api_helpers import (
    WRONG_OTP_CODE,
    CustomerFlowHarness,
    read_qr_token,
    store_ravi_electronics,
)
from tests.integration.api.customer.test_customer_session_endpoints import assert_problem

pytestmark = pytest.mark.integration

TIGHT_LIMIT_SETTINGS = ApplicationSettings(
    customer_session_start_rate_limit_max_requests=1,
    consent_otp_request_rate_limit_max_requests=1,
    customer_consent_rate_limit_max_requests=2,
)


@pytest.fixture
def tightly_limited_flow(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
) -> Iterator[CustomerFlowHarness]:
    """Runs the application with one QR exchange, one code request and two consents allowed."""
    with open_api_harness(
        session_factory, fixed_clock, mock_gateway, TIGHT_LIMIT_SETTINGS
    ) as harness:
        harness.client.app.dependency_overrides[provide_consent_reference_serial_generator] = (  # type: ignore[attr-defined]
            FixedConsentReferenceSerialGenerator
        )
        yield CustomerFlowHarness(api=harness, merchant_headers=store_ravi_electronics(harness))


def test_qr_exchanges_over_the_limit_answer_429_before_the_token_is_read(
    tightly_limited_flow: CustomerFlowHarness,
) -> None:
    """The second exchange in the window is refused even with a fresh, valid QR."""
    tightly_limited_flow.open_customer_session()
    response = tightly_limited_flow.exchange_qr(read_qr_token(tightly_limited_flow.start_sale()))
    assert_problem(response, 429, "RATE_LIMITED")
    assert response.headers["Retry-After"] == "60"


def test_code_requests_and_consent_attempts_over_the_limit_answer_429(
    tightly_limited_flow: CustomerFlowHarness,
) -> None:
    """One code request, then two consent attempts, per client and session in the window."""
    session = tightly_limited_flow.ready_for_consent()
    code_response = session.request_code()
    first_attempt = session.give_consent("consent-key-0000000001", otp=WRONG_OTP_CODE)
    second_attempt = session.give_consent("consent-key-0000000002", otp=WRONG_OTP_CODE)
    third_attempt = session.give_consent("consent-key-0000000003")
    assert_problem(code_response, 429, "RATE_LIMITED")
    assert code_response.headers["Retry-After"] == "600"
    assert_problem(first_attempt, 422, "OTP_INCORRECT")
    assert_problem(second_attempt, 422, "OTP_INCORRECT")
    assert_problem(third_attempt, 429, "RATE_LIMITED")
