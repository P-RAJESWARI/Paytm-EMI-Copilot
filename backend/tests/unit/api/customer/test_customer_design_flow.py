"""The design flow end to end over HTTP: the documented examples are what the stub answers."""

from typing import Any

from emi_copilot.api.controllers.customer_response_examples import (
    BUDGET_RESPONSE_EXAMPLE,
    COMFORT_CHECK_RESPONSE_EXAMPLE,
    CONSENT_RESPONSE_EXAMPLE,
    CUSTOMER_SESSION_RESPONSE_EXAMPLE,
    CUSTOMER_SESSION_SUMMARY_RESPONSE_EXAMPLE,
    OTP_CHALLENGE_RESPONSE_EXAMPLE,
    PLAN_ALTERNATIVES_RESPONSE_EXAMPLE,
    PLANS_RESPONSE_EXAMPLE,
    RECEIPT_RESPONSE_EXAMPLE,
)
from tests.unit.api.customer.conftest import RISKY_QR_TOKEN, CustomerApi


def test_design_flow_answers_exactly_the_documented_examples(customer_api: CustomerApi) -> None:
    """Session, budget, comfort, plans, alternatives, code, consent and receipt, in order."""
    session = customer_api.start_session()
    assert {**session.started_body, "sessionToken": "example"} == {
        **CUSTOMER_SESSION_RESPONSE_EXAMPLE,
        "sessionToken": "example",
    }
    assert session.confirm_budget().json() == BUDGET_RESPONSE_EXAMPLE
    comfort_response = session.run_comfort_check(has_customer_consented=True)
    assert comfort_response.json() == COMFORT_CHECK_RESPONSE_EXAMPLE
    assert session.get_plans().json() == PLANS_RESPONSE_EXAMPLE
    assert session.find_alternatives().json() == PLAN_ALTERNATIVES_RESPONSE_EXAMPLE
    assert session.request_code().json() == OTP_CHALLENGE_RESPONSE_EXAMPLE
    consent_response = session.give_consent()
    assert consent_response.status_code == 201
    assert {**consent_response.json(), "consentId": "example"} == {
        **CONSENT_RESPONSE_EXAMPLE,
        "consentId": "example",
    }
    assert session.get_receipt().json() == RECEIPT_RESPONSE_EXAMPLE
    summary_response = customer_api.client.get(session.base_path, headers=session.headers)
    assert summary_response.json() == CUSTOMER_SESSION_SUMMARY_RESPONSE_EXAMPLE


def test_design_plans_are_in_c4_order_with_design_amounts(customer_api: CustomerApi) -> None:
    """Cardless 3,350 bp fits; no-cost 66,667 paise above at 3,889; card 85,000 at 3,950."""
    session = customer_api.start_session()
    session.confirm_budget()
    session.run_comfort_check(has_customer_consented=True)
    plans = session.get_plans().json()["plans"]
    assert [
        (
            plan["offerId"],
            plan["amountAboveBudgetInPaise"],
            plan["comfort"]["comfortRatioInBasisPoints"],
        )
        for plan in plans
    ] == [
        ("mock-offer-cardless-12m", 0, 3350),
        ("mock-offer-no-cost-6m", 66_667, 3889),
        ("mock-offer-card-6m", 85_000, 3950),
    ]


def test_design_alternatives_give_engine_figures_not_the_mockup(customer_api: CustomerApi) -> None:
    """₹4,000 down gives 300,000 paise at 3,667 bp (not ₹2,999 / 36.6%); cardless 3,350."""
    session = customer_api.start_session()
    session.confirm_budget()
    session.run_comfort_check(has_customer_consented=True)
    alternatives = session.find_alternatives().json()["alternatives"]
    assert [
        (
            alternative["kind"],
            alternative["downPaymentInPaise"],
            alternative["monthlyInstallmentInPaise"],
            alternative["comfort"]["comfortRatioInBasisPoints"],
        )
        for alternative in alternatives
    ] == [
        ("DOWN_PAYMENT", 400_000, 300_000, 3667),
        ("LONGER_TENURE", 0, 205_000, 3350),
        ("CHEAPER_MODEL", 0, 300_000, 3667),
    ]


def test_consent_points_location_at_the_receipt_and_replays_identically(
    customer_api: CustomerApi,
) -> None:
    """201 with Location; the same key and body give the same 201 body again."""
    session = customer_api.start_session()
    session.confirm_budget()
    session.request_code()
    first_response = session.give_consent()
    replayed_response = session.give_consent()
    assert first_response.status_code == replayed_response.status_code == 201
    assert first_response.headers["Location"] == session.base_path + "/receipt"
    assert replayed_response.json() == first_response.json()
    assert session.get_receipt().json()["status"] == "READY_TO_PAY"


def test_receipt_has_no_payment_url(customer_api: CustomerApi) -> None:
    """The merchant takes payment on Paytm, so the customer gets no payment link."""
    session = customer_api.start_session()
    session.confirm_budget()
    session.request_code()
    session.give_consent()
    assert "paymentUrl" not in session.get_receipt().json()


def test_skipped_comfort_check_gives_null_comfort_everywhere(customer_api: CustomerApi) -> None:
    """Skipping returns no figures, and plans and alternatives carry no comfort."""
    session = customer_api.start_session()
    session.confirm_budget()
    comfort_body = session.run_comfort_check(has_customer_consented=False).json()
    plans_body = session.get_plans().json()
    alternatives_body = session.find_alternatives().json()
    assert comfort_body == {
        "status": "SKIPPED",
        "isSyntheticData": True,
        "monthlyInflowInPaise": None,
        "existingEmisInPaise": None,
    }
    assert not plans_body["hasComfortCheck"]
    assert all(plan["comfort"] is None for plan in plans_body["plans"])
    assert alternatives_body["basePlan"]["comfort"] is None
    assert all(item["comfort"] is None for item in alternatives_body["alternatives"])


def test_risky_qr_gives_plan_b_risky_at_5925(customer_api: CustomerApi) -> None:
    """The second sample customer (inflow ₹20,000) sees plan B at 59.25%, RISKY."""
    session = customer_api.start_session(RISKY_QR_TOKEN)
    session.confirm_budget()
    session.run_comfort_check(has_customer_consented=True)
    (card_plan,) = [
        plan
        for plan in session.get_plans().json()["plans"]
        if plan["offerId"] == "mock-offer-card-6m"
    ]
    assert card_plan["comfort"]["band"] == "RISKY"
    assert card_plan["comfort"]["comfortRatioInBasisPoints"] == 5925
    assert session.started_body["sessionCode"] == "4822"


def test_no_fit_budget_lists_every_plan_above_budget(customer_api: CustomerApi) -> None:
    """₹1,800: no plan fits, all three are listed with the amount above."""
    session = customer_api.start_session()
    session.confirm_budget(180_000)
    plans_body = session.get_plans().json()
    assert not plans_body["hasAnyPlanWithinBudget"]
    assert [plan["amountAboveBudgetInPaise"] for plan in plans_body["plans"]] == [
        25_000,
        186_667,
        205_000,
    ]


def consent_to_the_first_alternative_of_kind(
    customer_api: CustomerApi, kind: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Runs C2 to C9 and agrees to the C6 alternative of a kind, exactly as it was shown."""
    session = customer_api.start_session()
    session.confirm_budget()
    (alternative,) = [
        item for item in session.find_alternatives().json()["alternatives"] if item["kind"] == kind
    ]
    session.request_code()
    selection = {
        "downPaymentInPaise": alternative["downPaymentInPaise"],
        "productId": alternative["productId"],
        "shownMonthlyInstallmentInPaise": alternative["monthlyInstallmentInPaise"],
        "shownTotalPayableInPaise": alternative["totalPayableInPaise"],
    }
    consent_response = session.give_consent(offer_id=alternative["offerId"], selection=selection)
    assert consent_response.status_code == 201, consent_response.text
    return consent_response.json()["plan"], session.get_receipt().json()["plan"]


def test_consent_to_the_down_payment_alternative_records_that_selection(
    customer_api: CustomerApi,
) -> None:
    """₹4,000 down: ₹18,000 financed at ₹3,000.00 x 6 on the ₹22,000 phone, also on the receipt."""
    consented_plan, receipt_plan = consent_to_the_first_alternative_of_kind(
        customer_api, "DOWN_PAYMENT"
    )
    assert consented_plan == receipt_plan
    assert consented_plan["downPaymentInPaise"] == 400_000
    assert consented_plan["financedAmountInPaise"] == 1_800_000
    assert consented_plan["priceInPaise"] == 2_200_000
    assert consented_plan["regularInstallmentInPaise"] == 300_000
    assert consented_plan["lastInstallmentInPaise"] == 300_000
    assert consented_plan["productId"] == "stub-product-phone-128gb"


def test_consent_to_the_cheaper_model_alternative_records_that_product(
    customer_api: CustomerApi,
) -> None:
    """The 64 GB phone at ₹18,000 is the product on the consent and the receipt."""
    consented_plan, receipt_plan = consent_to_the_first_alternative_of_kind(
        customer_api, "CHEAPER_MODEL"
    )
    assert consented_plan == receipt_plan
    assert consented_plan["productId"] == "stub-product-phone-64gb"
    assert consented_plan["productName"] == "Example phone, 64 GB"
    assert consented_plan["priceInPaise"] == 1_800_000
    assert consented_plan["financedAmountInPaise"] == 1_800_000
    assert consented_plan["downPaymentInPaise"] == 0


def test_start_session_points_location_at_the_session_summary(customer_api: CustomerApi) -> None:
    """201 with Location; the summary there never repeats the token."""
    response = customer_api.client.post(
        "/api/v1/customer-sessions", json={"qrToken": "stub-qr-4821"}
    )
    location = response.headers["Location"]
    summary_response = customer_api.client.get(
        location, headers={"X-Customer-Session-Token": response.json()["sessionToken"]}
    )
    assert response.status_code == 201
    assert location == "/api/v1/customer-sessions/stub-customer-session-4821"
    assert summary_response.status_code == 200
    assert "sessionToken" not in summary_response.json()
    assert summary_response.json()["comfortCheckStatus"] is None


def test_rescan_keeps_consent_and_replays_the_original_consent(customer_api: CustomerApi) -> None:
    """A second scan gives a new token; the old key replays the first consent unchanged."""
    first_session = customer_api.start_session()
    first_session.confirm_budget()
    first_session.request_code()
    first_consent = first_session.give_consent().json()
    second_session = customer_api.start_session()
    replayed_response = second_session.give_consent()
    summary = customer_api.client.get(
        second_session.base_path, headers=second_session.headers
    ).json()
    assert replayed_response.status_code == 201
    assert replayed_response.json()["consentId"] == first_consent["consentId"]
    assert summary["hasConsented"]
    assert summary["hasConfirmedBudget"]
    assert first_session.get_plans().status_code == 401
