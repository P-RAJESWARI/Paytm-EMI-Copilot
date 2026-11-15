"""The one-time code, consent as evidence and the receipt over HTTP, with every calm refusal."""

from datetime import timedelta

import pytest

from tests.integration.api.customer.customer_api_helpers import (
    CARDLESS_OFFER_ID,
    WRONG_OTP_CODE,
    CustomerFlowHarness,
)
from tests.integration.api.customer.test_customer_session_endpoints import assert_problem

pytestmark = pytest.mark.integration


def test_requesting_the_code_names_the_phone_ending_and_the_tries(
    customer_flow: CustomerFlowHarness,
) -> None:
    """The Mock phone ends 42; the code lasts 5 minutes, resends after 30 s, allows 3 tries."""
    session = customer_flow.open_customer_session()
    session.confirm_budget()
    response = session.request_code()
    assert response.status_code == 200, response.text
    assert response.json() == {
        "phoneLastTwoDigits": "42",
        "expiresAt": "2026-11-15T09:35:00Z",
        "resendAvailableAt": "2026-11-15T09:30:30Z",
        "attemptsRemaining": 3,
    }


def test_asking_for_a_new_code_too_early_answers_429_with_retry_after(
    customer_flow: CustomerFlowHarness,
) -> None:
    """A new code waits 30 seconds after the last; the answer says how long is left."""
    session = customer_flow.ready_for_consent()
    customer_flow.api.clock.advance(timedelta(seconds=10))
    too_early_response = session.request_code()
    customer_flow.api.clock.advance(timedelta(seconds=20))
    assert_problem(too_early_response, 429, "OTP_RESEND_NOT_YET_AVAILABLE")
    assert too_early_response.headers["Retry-After"] == "20"
    assert session.request_code().status_code == 200


def test_a_wrong_code_answers_422_with_the_tries_left_then_the_code_is_spent(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Two wrong tries say 2 then 1 left; the third spends the code (OTP_EXPIRED), no lockout."""
    session = customer_flow.ready_for_consent()
    first_wrong = session.give_consent("consent-key-0000000001", otp=WRONG_OTP_CODE)
    second_wrong = session.give_consent("consent-key-0000000002", otp=WRONG_OTP_CODE)
    third_wrong = session.give_consent("consent-key-0000000003", otp=WRONG_OTP_CODE)
    assert_problem(first_wrong, 422, "OTP_INCORRECT")
    assert first_wrong.json()["attemptsRemaining"] == 2
    assert second_wrong.json()["attemptsRemaining"] == 1
    assert_problem(third_wrong, 422, "OTP_EXPIRED")
    assert "attemptsRemaining" not in third_wrong.json()
    assert_problem(session.give_consent("consent-key-0000000004"), 422, "OTP_EXPIRED")
    assert session.request_code().status_code == 200
    assert session.give_consent("consent-key-0000000005").status_code == 201


def test_an_expired_code_answers_422(customer_flow: CustomerFlowHarness) -> None:
    """The code lasts 5 minutes."""
    session = customer_flow.ready_for_consent()
    customer_flow.api.clock.advance(timedelta(minutes=5))
    assert_problem(session.give_consent(), 422, "OTP_EXPIRED")


def test_consent_without_requesting_a_code_answers_422(customer_flow: CustomerFlowHarness) -> None:
    """The code must be requested first."""
    session = customer_flow.open_customer_session()
    session.confirm_budget()
    assert_problem(session.give_consent(), 422, "OTP_NOT_REQUESTED")


def test_consent_without_idempotency_key_answers_422(customer_flow: CustomerFlowHarness) -> None:
    """Consent records evidence, so the Idempotency-Key header is required."""
    response = customer_flow.ready_for_consent().give_consent(idempotency_key=None)
    assert_problem(response, 422, "REQUEST_VALIDATION_FAILED")
    assert response.json()["fieldErrors"][0]["field"] == "Idempotency-Key"


def test_consent_without_agreeing_or_with_removed_fields_answers_422(
    customer_flow: CustomerFlowHarness,
) -> None:
    """HasAgreedToPlan must be true, and productId or downPaymentInPaise no longer exist."""
    session = customer_flow.ready_for_consent()
    base_body = {
        "offerId": "mock-offer-no-cost-6m",
        "otp": "123456",
        "shownMonthlyInstallmentInPaise": 366_667,
        "shownTotalPayableInPaise": 2_200_000,
    }
    for index, body in enumerate(
        (
            {**base_body, "hasAgreedToPlan": False},
            {**base_body, "hasAgreedToPlan": True, "downPaymentInPaise": 400_000},
            {**base_body, "hasAgreedToPlan": True, "productId": "01JCPRODUCTRAVI00000000001"},
        )
    ):
        response = customer_flow.api.client.post(
            session.base_path + "/consent",
            json=body,
            headers={**session.headers, "Idempotency-Key": f"consent-key-refused-{index:04d}"},
        )
        assert_problem(response, 422, "REQUEST_VALIDATION_FAILED")


def test_consent_to_an_offer_not_quoted_for_the_item_answers_422(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Only a plan quoted for the session's item at the sale price can be agreed to."""
    response = customer_flow.ready_for_consent().give_consent(offer_id="offer-not-quoted")
    assert_problem(response, 422, "INVALID_PLAN_SELECTION")


def test_consent_with_figures_that_were_not_quoted_answers_409(
    customer_flow: CustomerFlowHarness,
) -> None:
    """A shown monthly that a fresh quote does not match records nothing."""
    session = customer_flow.ready_for_consent()
    response = session.give_consent(
        shown_figures={
            "shownMonthlyInstallmentInPaise": 366_700,
            "shownTotalPayableInPaise": 2_200_000,
        }
    )
    assert_problem(response, 409, "SHOWN_PLAN_CHANGED")
    assert session.get_summary().json()["hasConsented"] is False


def test_consent_to_the_longer_tenure_alternative_is_recorded_as_shown(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Longer tenure is another offer on the same item, so it can be agreed (ADR 0022)."""
    session = customer_flow.ready_for_consent()
    response = session.give_consent(
        offer_id=CARDLESS_OFFER_ID,
        shown_figures={
            "shownMonthlyInstallmentInPaise": 205_000,
            "shownTotalPayableInPaise": 2_460_000,
        },
    )
    assert response.status_code == 201, response.text
    plan = response.json()["plan"]
    assert (plan["regularInstallmentInPaise"], plan["lastInstallmentInPaise"]) == (205_000, 205_000)
    assert (plan["extraInTotalInPaise"], plan["totalPayableInPaise"]) == (260_000, 2_460_000)
    assert (plan["downPaymentInPaise"], plan["financedAmountInPaise"]) == (0, 2_200_000)


def test_consent_replays_with_the_same_key_and_refuses_a_second_consent(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Same key: the same 201 (even with another code). New key: 409. Other body: 422."""
    session = customer_flow.ready_for_consent()
    first_response = session.give_consent()
    replayed_response = session.give_consent(otp=WRONG_OTP_CODE)
    second_key_response = session.give_consent("consent-key-0000000002")
    other_body_response = session.give_consent(offer_id=CARDLESS_OFFER_ID)
    assert first_response.status_code == replayed_response.status_code == 201
    assert replayed_response.json() == first_response.json()
    assert first_response.headers["Location"] == session.base_path + "/receipt"
    assert_problem(second_key_response, 409, "CONSENT_ALREADY_GIVEN")
    assert_problem(other_body_response, 422, "IDEMPOTENCY_KEY_REUSED")


def test_after_consent_the_steps_before_it_are_closed(customer_flow: CustomerFlowHarness) -> None:
    """Budget, plans and a new code answer 409 once the plan is agreed."""
    session = customer_flow.ready_for_consent()
    session.give_consent()
    assert_problem(session.confirm_budget(), 409, "CONSENT_ALREADY_GIVEN")
    assert_problem(session.get_plans(), 409, "CONSENT_ALREADY_GIVEN")
    assert_problem(session.request_code(), 409, "CONSENT_ALREADY_GIVEN")


def test_receipt_before_consent_answers_409(customer_flow: CustomerFlowHarness) -> None:
    """There is no receipt until the plan is agreed."""
    assert_problem(customer_flow.open_customer_session().get_receipt(), 409, "CONSENT_NOT_GIVEN")


def test_receipt_after_consent_is_the_hand_off_with_no_payment_url(
    customer_flow: CustomerFlowHarness,
) -> None:
    """READY_TO_PAY with the frozen plan, the phone ending and the placeholder cooling-off note."""
    session = customer_flow.ready_for_consent()
    consent_body = session.give_consent(accept_language="ta").json()
    receipt_body = session.get_receipt().json()
    assert receipt_body["status"] == "READY_TO_PAY"
    assert receipt_body["plan"] == consent_body["plan"]
    assert receipt_body["reference"] == consent_body["reference"] == "EMI-1511-0042"
    assert receipt_body["phoneLastTwoDigits"] == "42"
    assert receipt_body["coolingOffNoticeStatus"] == "PLACEHOLDER"
    assert "paymentUrl" not in receipt_body
