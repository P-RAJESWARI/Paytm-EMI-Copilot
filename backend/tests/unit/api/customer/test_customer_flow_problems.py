"""Every refusal of the customer flow is application/problem+json with a stable code."""

from collections.abc import Callable
from datetime import timedelta

import httpx
import pytest

from tests.unit.api.customer.conftest import (
    SESSION_TOKEN_HEADER,
    CustomerApi,
    CustomerSessionClient,
)


def assert_problem(response: httpx.Response, status: int, code: str) -> None:
    """Checks the status, the problem media type and the stable code."""
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code


def ready_for_consent(customer_api: CustomerApi) -> CustomerSessionClient:
    """Starts a session, confirms ₹3,000 and requests the code."""
    session = customer_api.start_session()
    session.confirm_budget()
    session.request_code()
    return session


def test_start_session_with_an_unknown_qr_answers_401(customer_api: CustomerApi) -> None:
    """An unknown QR is a calm 401 asking for a new QR."""
    response = customer_api.client.post(
        "/api/v1/customer-sessions", json={"qrToken": "stub-qr-0000"}
    )
    assert_problem(response, 401, "CUSTOMER_QR_TOKEN_INVALID")
    assert "ask the shop for a new QR" in response.json()["detail"]


@pytest.mark.parametrize(
    "send_request",
    [
        lambda session: session.client.get(session.base_path + "/plans"),
        lambda session: session.client.put(
            session.base_path + "/budget",
            json={"monthlyBudgetInPaise": 300_000, "hasCustomerConfirmed": True},
        ),
        lambda session: session.client.get(session.base_path + "/receipt"),
        lambda session: session.client.post(session.base_path + "/consent/otp"),
    ],
    ids=["plans", "budget", "receipt", "otp"],
)
def test_request_without_session_token_answers_401(
    customer_api: CustomerApi, send_request: Callable[[CustomerSessionClient], httpx.Response]
) -> None:
    """A missing X-Customer-Session-Token is our 401 problem, never a framework 403."""
    assert_problem(
        send_request(customer_api.start_session()), 401, "CUSTOMER_SESSION_TOKEN_INVALID"
    )


def test_request_with_a_wrong_session_token_answers_401(customer_api: CustomerApi) -> None:
    """A token that does not match the session is refused."""
    session = customer_api.start_session()
    response = customer_api.client.get(
        session.base_path + "/plans", headers={SESSION_TOKEN_HEADER: "stub-wrong"}
    )
    assert_problem(response, 401, "CUSTOMER_SESSION_TOKEN_INVALID")


def test_request_after_the_session_ended_answers_401(customer_api: CustomerApi) -> None:
    """A session ends 30 minutes after the QR was scanned."""
    session = customer_api.start_session()
    customer_api.clock.advance(timedelta(minutes=30))
    assert_problem(session.confirm_budget(), 401, "CUSTOMER_SESSION_TOKEN_INVALID")


def test_request_for_an_unknown_session_answers_404(customer_api: CustomerApi) -> None:
    """A session id nobody started is not found."""
    session = customer_api.start_session()
    response = customer_api.client.get(
        "/api/v1/customer-sessions/stub-customer-session-0000/plans", headers=session.headers
    )
    assert_problem(response, 404, "CUSTOMER_SESSION_NOT_FOUND")


@pytest.mark.parametrize(
    "send_request",
    [
        CustomerSessionClient.get_plans,
        CustomerSessionClient.find_alternatives,
        lambda session: session.run_comfort_check(has_customer_consented=True),
    ],
    ids=["plans", "alternatives", "comfort-check"],
)
def test_advice_before_a_budget_answers_409(
    customer_api: CustomerApi, send_request: Callable[[CustomerSessionClient], httpx.Response]
) -> None:
    """Plans, alternatives and the comfort check come after the budget."""
    assert_problem(send_request(customer_api.start_session()), 409, "BUDGET_NOT_CONFIRMED")


def test_budget_not_confirmed_by_the_customer_answers_422(customer_api: CustomerApi) -> None:
    """The customer must confirm the budget: hasCustomerConfirmed false is refused."""
    session = customer_api.start_session()
    response = customer_api.client.put(
        session.base_path + "/budget",
        json={"monthlyBudgetInPaise": 300_000, "hasCustomerConfirmed": False},
        headers=session.headers,
    )
    assert_problem(response, 422, "REQUEST_VALIDATION_FAILED")


def test_budget_as_a_float_answers_422(customer_api: CustomerApi) -> None:
    """Money is a JSON integer of paise; 3000.0 is refused."""
    session = customer_api.start_session()
    response = customer_api.client.put(
        session.base_path + "/budget",
        json={"monthlyBudgetInPaise": 3000.0, "hasCustomerConfirmed": True},
        headers=session.headers,
    )
    assert_problem(response, 422, "REQUEST_VALIDATION_FAILED")


def test_consent_without_idempotency_key_answers_422(customer_api: CustomerApi) -> None:
    """Consent records evidence, so the Idempotency-Key header is required."""
    session = ready_for_consent(customer_api)
    response = session.give_consent(idempotency_key=None)
    assert_problem(response, 422, "REQUEST_VALIDATION_FAILED")
    assert response.json()["fieldErrors"][0]["field"] == "Idempotency-Key"


def test_consent_with_a_wrong_code_answers_422(customer_api: CustomerApi) -> None:
    """A wrong code is a calm 422 that offers a new code."""
    response = ready_for_consent(customer_api).give_consent(otp="654321")
    assert_problem(response, 422, "OTP_INCORRECT")


def test_consent_with_an_expired_code_answers_422(customer_api: CustomerApi) -> None:
    """The code lasts 5 minutes."""
    session = ready_for_consent(customer_api)
    customer_api.clock.advance(timedelta(minutes=5))
    assert_problem(session.give_consent(), 422, "OTP_EXPIRED")


def test_consent_without_requesting_a_code_answers_422(customer_api: CustomerApi) -> None:
    """The code must be requested first."""
    session = customer_api.start_session()
    session.confirm_budget()
    assert_problem(session.give_consent(), 422, "OTP_NOT_REQUESTED")


def test_consent_to_an_unknown_offer_answers_404(customer_api: CustomerApi) -> None:
    """Only a quoted plan can be agreed to."""
    response = ready_for_consent(customer_api).give_consent(offer_id="offer-not-quoted")
    assert_problem(response, 404, "OFFER_NOT_FOUND")


def test_alternatives_for_an_unknown_offer_answer_404(customer_api: CustomerApi) -> None:
    """Alternatives are found only for a quoted plan."""
    session = customer_api.start_session()
    session.confirm_budget()
    assert_problem(session.find_alternatives("offer-not-quoted"), 404, "OFFER_NOT_FOUND")


def test_second_consent_under_a_new_key_answers_409(customer_api: CustomerApi) -> None:
    """Consent happens once per session."""
    session = ready_for_consent(customer_api)
    session.give_consent()
    assert_problem(
        session.give_consent(idempotency_key="stub-consent-key-0002"), 409, "CONSENT_ALREADY_GIVEN"
    )


def test_same_key_with_another_body_answers_422(customer_api: CustomerApi) -> None:
    """A key reused for another plan is refused."""
    session = ready_for_consent(customer_api)
    session.give_consent()
    response = session.give_consent(offer_id="mock-offer-cardless-12m")
    assert_problem(response, 422, "IDEMPOTENCY_KEY_REUSED")


def test_receipt_before_consent_answers_409(customer_api: CustomerApi) -> None:
    """There is no receipt until the plan is agreed."""
    assert_problem(customer_api.start_session().get_receipt(), 409, "CONSENT_NOT_GIVEN")


def test_consent_without_agreeing_answers_422(customer_api: CustomerApi) -> None:
    """The customer must agree: hasAgreedToPlan false is refused."""
    session = ready_for_consent(customer_api)
    response = customer_api.client.post(
        session.base_path + "/consent",
        json={"offerId": "mock-offer-no-cost-6m", "otp": "123456", "hasAgreedToPlan": False},
        headers={**session.headers, "Idempotency-Key": "stub-consent-key-0003"},
    )
    assert_problem(response, 422, "REQUEST_VALIDATION_FAILED")


def test_consent_with_figures_that_were_not_quoted_answers_409(customer_api: CustomerApi) -> None:
    """A shown monthly that a fresh quote does not match records nothing."""
    response = ready_for_consent(customer_api).give_consent(
        selection={"shownMonthlyInstallmentInPaise": 366_700, "shownTotalPayableInPaise": 2_200_000}
    )
    assert_problem(response, 409, "SHOWN_PLAN_CHANGED")


def test_consent_with_a_down_payment_not_offered_answers_422(customer_api: CustomerApi) -> None:
    """Only zero or the suggested down payment can be agreed to."""
    response = ready_for_consent(customer_api).give_consent(
        selection={
            "downPaymentInPaise": 123_400,
            "shownMonthlyInstallmentInPaise": 300_000,
            "shownTotalPayableInPaise": 1_800_000,
        }
    )
    assert_problem(response, 422, "INVALID_PLAN_SELECTION")


def test_consent_for_an_unknown_product_answers_422(customer_api: CustomerApi) -> None:
    """Only the session's item and the offered cheaper model can be agreed to."""
    response = ready_for_consent(customer_api).give_consent(
        selection={
            "productId": "stub-product-other",
            "shownMonthlyInstallmentInPaise": 366_667,
            "shownTotalPayableInPaise": 2_200_000,
        }
    )
    assert_problem(response, 422, "INVALID_PLAN_SELECTION")


def test_consent_replay_with_another_code_returns_the_original(customer_api: CustomerApi) -> None:
    """The same key and selection with a different code is the same request."""
    session = ready_for_consent(customer_api)
    first_response = session.give_consent()
    replayed_response = session.give_consent(otp="654321")
    assert replayed_response.status_code == 201
    assert replayed_response.json() == first_response.json()
