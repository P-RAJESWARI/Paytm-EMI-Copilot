"""The QR exchange and the session: single-use, token-guarded, and one answer to probing."""

from datetime import timedelta

import httpx
import pytest

from tests.integration.api.customer.customer_api_helpers import (
    CUSTOMER_SESSIONS_PATH,
    SESSION_TOKEN_HEADER,
    CustomerFlowHarness,
    CustomerSessionClient,
    read_qr_token,
)

pytestmark = pytest.mark.integration


def assert_problem(response: httpx.Response, status: int, code: str) -> None:
    """Checks the status, the problem media type and the stable code."""
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code


def test_exchanging_the_qr_opens_a_session_and_points_location_at_it(
    customer_flow: CustomerFlowHarness,
) -> None:
    """201 with the C1 facts; the summary at Location never repeats the token."""
    sale_body = customer_flow.start_sale()
    response = customer_flow.exchange_qr(read_qr_token(sale_body))
    body = response.json()
    summary_response = customer_flow.api.client.get(
        response.headers["Location"], headers={SESSION_TOKEN_HEADER: body["sessionToken"]}
    )
    assert response.status_code == 201
    assert response.headers["Location"] == f"{CUSTOMER_SESSIONS_PATH}/{body['customerSessionId']}"
    assert body["shopName"] == "Ravi Electronics"
    assert body["productName"] == "Example phone, 128 GB"
    assert body["priceInPaise"] == 2_200_000
    assert body["sessionCode"] == sale_body["sessionCode"]
    assert body["expiresAt"] == "2026-11-15T10:00:00Z"
    assert summary_response.status_code == 200
    assert "sessionToken" not in summary_response.json()
    assert summary_response.json()["comfortCheckStatus"] is None
    assert summary_response.json()["hasConfirmedBudget"] is False


def test_a_qr_exchanged_once_cannot_be_exchanged_again(
    customer_flow: CustomerFlowHarness,
) -> None:
    """The QR is single-use (ADR 0022 decision 4): the second exchange is a calm 401."""
    sale_body = customer_flow.start_sale()
    customer_flow.open_customer_session(sale_body)
    response = customer_flow.exchange_qr(read_qr_token(sale_body))
    assert_problem(response, 401, "CUSTOMER_QR_TOKEN_INVALID")
    assert "ask the shop for a new QR" in response.json()["detail"]


def test_a_forged_qr_answers_401(customer_flow: CustomerFlowHarness) -> None:
    """A token not signed by this server is refused like any other bad QR."""
    assert_problem(customer_flow.exchange_qr("forged.token"), 401, "CUSTOMER_QR_TOKEN_INVALID")


def test_a_new_qr_ends_the_earlier_session_of_the_sale(customer_flow: CustomerFlowHarness) -> None:
    """The shop re-issues the QR; the first phone's session stops working."""
    sale_body = customer_flow.start_sale()
    first_session = customer_flow.open_customer_session(sale_body)
    reissue_response = customer_flow.api.client.post(
        f"/api/v1/sales/{sale_body['saleId']}/qr-tokens", headers=customer_flow.merchant_headers
    )
    second_session = customer_flow.open_customer_session(
        {**sale_body, "qr": reissue_response.json()}
    )
    assert_problem(first_session.get_summary(), 401, "CUSTOMER_SESSION_TOKEN_INVALID")
    assert second_session.get_summary().status_code == 200


@pytest.mark.parametrize(
    "path_suffix", ["", "/plans", "/receipt"], ids=["summary", "plans", "receipt"]
)
def test_a_missing_or_wrong_session_token_answers_401(
    customer_flow: CustomerFlowHarness, path_suffix: str
) -> None:
    """No token, or a token that opens no session, is our 401 problem, never a framework 403."""
    session = customer_flow.open_customer_session()
    client = customer_flow.api.client
    assert_problem(
        client.get(session.base_path + path_suffix), 401, "CUSTOMER_SESSION_TOKEN_INVALID"
    )
    assert_problem(
        client.get(session.base_path + path_suffix, headers={SESSION_TOKEN_HEADER: "wrong"}),
        401,
        "CUSTOMER_SESSION_TOKEN_INVALID",
    )


def test_a_session_ends_thirty_minutes_after_the_exchange(
    customer_flow: CustomerFlowHarness,
) -> None:
    """After its lifetime the token no longer opens the session."""
    session = customer_flow.open_customer_session()
    customer_flow.api.clock.advance(timedelta(minutes=30))
    assert_problem(session.confirm_budget(), 401, "CUSTOMER_SESSION_TOKEN_INVALID")


def test_probing_another_session_id_gives_one_answer_whether_it_exists_or_not(
    customer_flow: CustomerFlowHarness,
) -> None:
    """A valid token with any other id is the same 404, so session ids cannot be probed."""
    first_session = customer_flow.open_customer_session()
    other_session = customer_flow.open_customer_session()
    client = customer_flow.api.client
    existing_other = client.get(other_session.base_path, headers=first_session.headers)
    missing_other = client.get(
        f"{CUSTOMER_SESSIONS_PATH}/01JCNOSUCHSESSION000000000", headers=first_session.headers
    )
    assert_problem(existing_other, 404, "CUSTOMER_SESSION_NOT_FOUND")
    assert_problem(missing_other, 404, "CUSTOMER_SESSION_NOT_FOUND")
    assert {**existing_other.json(), "correlationId": None} == {
        **missing_other.json(),
        "correlationId": None,
    }


def test_the_qr_token_is_never_logged(
    customer_flow: CustomerFlowHarness, caplog: pytest.LogCaptureFixture
) -> None:
    """Neither the QR token nor the session token reaches any log line (never-log list)."""
    sale_body = customer_flow.start_sale()
    qr_token = read_qr_token(sale_body)
    with caplog.at_level("DEBUG"):
        response = customer_flow.exchange_qr(qr_token)
        session = CustomerSessionClient(
            customer_flow.api.client,
            sale_body["saleId"],
            response.json()["customerSessionId"],
            response.json()["sessionToken"],
            response.json(),
        )
        session.get_summary()
        customer_flow.exchange_qr(qr_token)
    logged_text = " ".join(f"{record.getMessage()} {record.__dict__}" for record in caplog.records)
    assert qr_token not in logged_text
    assert session.session_token not in logged_text
