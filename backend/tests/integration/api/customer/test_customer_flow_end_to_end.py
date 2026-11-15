"""The whole design flow over HTTP: the shop starts a sale, the customer agrees on their phone.

Merchant pairing, sale and QR; customer exchange, ₹3,000 budget, comfort check, plans,
alternatives, explanation, a wrong code then the Mock code, consent; then what the shop sees,
the receipt, the single-use QR, the consent replay, the evidence chain and the funnel rows.
"""

from typing import Any

import pytest

from emi_copilot.domain.consent import verify_consent_record_chain
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.api.customer.customer_api_helpers import (
    NO_COST_OFFER_ID,
    WRONG_OTP_CODE,
    CustomerFlowHarness,
    CustomerSessionClient,
    read_qr_token,
)
from tests.integration.api.customer.test_customer_session_endpoints import assert_problem

pytestmark = pytest.mark.integration

CONSENT_KEY = "design-flow-consent-key-0001"
PLAN_A_AS_THE_MERCHANT_SEES_IT = {
    "offerId": NO_COST_OFFER_ID,
    "planKind": "NO_COST",
    "lenderLabel": "Brand",
    "tenureInMonths": 6,
    "monthlyInstallmentInPaise": 366_667,
    "extraInTotalInPaise": 0,
    "totalPayableInPaise": 2_200_000,
}


def run_design_customer_flow(
    customer_flow: CustomerFlowHarness,
) -> tuple[dict[str, Any], CustomerSessionClient, dict[str, Any]]:
    """Plays C1 to C9 with the comfort check allowed; gives the sale, the session and consent."""
    sale_body = customer_flow.start_sale()
    session = customer_flow.open_customer_session(sale_body)
    assert session.confirm_budget(300_000).status_code == 200
    assert session.answer_comfort_check(has_customer_consented=True).status_code == 200
    plans_body = session.get_plans().json()
    assert [
        (plan["offerId"], plan["comfort"]["comfortRatioInBasisPoints"])
        for plan in plans_body["plans"]
    ] == [
        ("mock-offer-cardless-12m", 3350),
        (NO_COST_OFFER_ID, 3889),
        ("mock-offer-card-6m", 3950),
    ]
    assert session.find_alternatives().status_code == 200
    assert session.explain(accept_language="ta").json()["language"] == "ta"
    assert session.request_code().status_code == 200
    wrong_code_response = session.give_consent(CONSENT_KEY, otp=WRONG_OTP_CODE)
    assert_problem(wrong_code_response, 422, "OTP_INCORRECT")
    assert wrong_code_response.json()["attemptsRemaining"] == 2
    consent_response = session.give_consent(CONSENT_KEY, accept_language="ta")
    assert consent_response.status_code == 201, consent_response.text
    return sale_body, session, consent_response.json()


def test_design_flow_ends_ready_to_pay_for_the_shop_with_the_agreed_plan(
    customer_flow: CustomerFlowHarness,
) -> None:
    """The shop sees READY_TO_PAY and plan A; the customer's receipt says the same."""
    sale_body, session, consent_body = run_design_customer_flow(customer_flow)
    merchant_sale = customer_flow.read_merchant_sale(sale_body["saleId"])
    receipt_body = session.get_receipt().json()
    assert merchant_sale["status"] == "READY_TO_PAY"
    assert merchant_sale["chosenPlan"] == PLAN_A_AS_THE_MERCHANT_SEES_IT
    assert receipt_body["status"] == consent_body["status"] == "READY_TO_PAY"
    assert receipt_body["plan"] == consent_body["plan"]
    assert consent_body["plan"]["regularInstallmentInPaise"] == 366_667
    assert consent_body["plan"]["lastInstallmentInPaise"] == 366_665


def test_after_the_flow_the_qr_is_spent_and_the_consent_replays(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Scanning the same QR again is 401; the same Idempotency-Key gives back the same consent."""
    sale_body, session, consent_body = run_design_customer_flow(customer_flow)
    reuse_response = customer_flow.exchange_qr(read_qr_token(sale_body))
    replay_response = session.give_consent(CONSENT_KEY, otp=WRONG_OTP_CODE)
    assert_problem(reuse_response, 401, "CUSTOMER_QR_TOKEN_INVALID")
    assert replay_response.status_code == 201
    assert replay_response.json()["consentId"] == consent_body["consentId"]


def test_the_consent_evidence_chain_verifies_and_holds_the_customer_language(
    customer_flow: CustomerFlowHarness,
) -> None:
    """One hash-chained record for the sale, intact, in Tamil as the phone asked."""
    sale_body, _, consent_body = run_design_customer_flow(customer_flow)
    harness = customer_flow.api
    with SqlAlchemyUnitOfWork(harness.session_factory, harness.clock) as unit_of_work:
        records = unit_of_work.consent_records.list_in_order()
    assert verify_consent_record_chain(records).is_intact
    (record,) = [item for item in records if item.evidence.sale_id == sale_body["saleId"]]
    assert record.evidence.consent_id == consent_body["consentId"]
    assert record.evidence.language.value == "ta"
    assert record.evidence.phone_last_two_digits == "42"


def test_the_funnel_records_each_stage_of_the_sale_once(
    customer_flow: CustomerFlowHarness,
) -> None:
    """STARTED, BUDGET_TOLD with the ₹3,000 budget, PLANS_VIEWED and AGREED, one row each."""
    sale_body, session, _ = run_design_customer_flow(customer_flow)
    session.get_receipt()
    harness = customer_flow.api
    with SqlAlchemyUnitOfWork(harness.session_factory, harness.clock) as unit_of_work:
        funnel_events = unit_of_work.funnel_events.list_for_sale(sale_body["saleId"])
    assert [event.stage for event in funnel_events] == [
        FunnelStage.STARTED,
        FunnelStage.BUDGET_TOLD,
        FunnelStage.PLANS_VIEWED,
        FunnelStage.AGREED,
    ]
    (budget_event,) = [event for event in funnel_events if event.stage is FunnelStage.BUDGET_TOLD]
    assert budget_event.monthly_budget is not None
    assert budget_event.monthly_budget.to_paise() == 300_000
