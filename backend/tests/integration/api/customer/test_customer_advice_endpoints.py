"""Budget, comfort check, plans, alternatives and explanation over HTTP on the design data."""

from collections.abc import Callable

import httpx
import pytest

from tests.integration.api.customer.customer_api_helpers import (
    CARDLESS_OFFER_ID,
    CustomerFlowHarness,
    CustomerSessionClient,
)
from tests.integration.api.customer.test_customer_session_endpoints import assert_problem

pytestmark = pytest.mark.integration


def test_design_plans_are_in_c4_order_with_the_engine_figures(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Cardless 3,350 bp fits; no-cost 66,667 paise above at 3,889; card 85,000 at 3,950."""
    session = customer_flow.open_customer_session()
    session.confirm_budget()
    session.answer_comfort_check(has_customer_consented=True)
    plans = session.get_plans().json()["plans"]
    assert [
        (
            plan["offerId"],
            plan["amountAboveBudgetInPaise"],
            plan["comfort"]["comfortRatioInBasisPoints"],
            plan["comfort"]["band"],
        )
        for plan in plans
    ] == [
        ("mock-offer-cardless-12m", 0, 3350, "COMFORTABLE"),
        ("mock-offer-no-cost-6m", 66_667, 3889, "STRETCHING"),
        ("mock-offer-card-6m", 85_000, 3950, "STRETCHING"),
    ]


def test_design_alternatives_give_engine_figures_not_the_mockup(
    customer_flow: CustomerFlowHarness,
) -> None:
    """₹4,000 down gives 300,000 paise at 3,667 bp (never ₹2,999 / 36.6%); the 64 GB phone too."""
    session = customer_flow.open_customer_session()
    session.confirm_budget()
    session.answer_comfort_check(has_customer_consented=True)
    alternatives = session.find_alternatives().json()["alternatives"]
    assert [
        (
            alternative["kind"],
            alternative["downPaymentInPaise"],
            alternative["monthlyInstallmentInPaise"],
            alternative["comfort"]["comfortRatioInBasisPoints"],
            alternative["productName"],
        )
        for alternative in alternatives
    ] == [
        ("DOWN_PAYMENT", 400_000, 300_000, 3667, None),
        ("LONGER_TENURE", 0, 205_000, 3350, None),
        ("CHEAPER_MODEL", 0, 300_000, 3667, "Example phone, 64 GB"),
    ]


def test_skipped_comfort_check_gives_null_comfort_everywhere(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Skipping returns no figures, and plans and alternatives carry no comfort."""
    session = customer_flow.open_customer_session()
    session.confirm_budget()
    comfort_body = session.answer_comfort_check(has_customer_consented=False).json()
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
    assert session.get_summary().json()["comfortCheckStatus"] == "SKIPPED"


def test_no_fit_budget_lists_every_plan_above_budget(customer_flow: CustomerFlowHarness) -> None:
    """₹1,800: no plan fits, and all three are listed with the amount above."""
    session = customer_flow.open_customer_session()
    session.confirm_budget(180_000)
    plans_body = session.get_plans().json()
    assert not plans_body["hasAnyPlanWithinBudget"]
    assert [plan["amountAboveBudgetInPaise"] for plan in plans_body["plans"]] == [
        25_000,
        186_667,
        205_000,
    ]


@pytest.mark.parametrize(
    ("accept_language", "expected_language", "expected_monthly_text"),
    [
        (None, "en", "you pay ₹2,050 each month for 12 months"),
        ("ta-IN,ta;q=0.9,en;q=0.8", "ta", "₹2,050"),
        ("hi-IN", "en", "you pay ₹2,050 each month for 12 months"),
    ],
)
def test_explanation_follows_accept_language_and_highlights_engine_figures(
    customer_flow: CustomerFlowHarness,
    accept_language: str | None,
    expected_language: str,
    expected_monthly_text: str,
) -> None:
    """The template text names the monthly and the extra exactly as the engine computed them."""
    session = customer_flow.open_customer_session()
    response = session.explain(CARDLESS_OFFER_ID, accept_language)
    body = response.json()
    assert response.status_code == 200, response.text
    assert body["language"] == expected_language
    assert body["source"] == "TEMPLATE"
    assert expected_monthly_text in body["text"]
    assert "₹2,600" in body["text"]
    assert body["highlightedAmounts"] == [
        {"kind": "MONTHLY_INSTALLMENT", "amountInPaise": 205_000},
        {"kind": "EXTRA_IN_TOTAL", "amountInPaise": 260_000},
    ]


@pytest.mark.parametrize(
    "send_request",
    [
        CustomerSessionClient.get_plans,
        CustomerSessionClient.find_alternatives,
        lambda session: session.answer_comfort_check(has_customer_consented=True),
        CustomerSessionClient.request_code,
    ],
    ids=["plans", "alternatives", "comfort-check", "otp"],
)
def test_steps_before_a_budget_answer_409(
    customer_flow: CustomerFlowHarness,
    send_request: Callable[[CustomerSessionClient], httpx.Response],
) -> None:
    """Plans, alternatives, the comfort check and the code come after the budget."""
    assert_problem(send_request(customer_flow.open_customer_session()), 409, "BUDGET_NOT_CONFIRMED")


@pytest.mark.parametrize(
    "budget_body",
    [
        {"monthlyBudgetInPaise": 300_000, "hasCustomerConfirmed": False},
        {"monthlyBudgetInPaise": 3000.0, "hasCustomerConfirmed": True},
        {"monthlyBudgetInPaise": 0, "hasCustomerConfirmed": True},
    ],
    ids=["not-confirmed", "float", "zero"],
)
def test_budget_that_is_not_confirmed_integer_paise_answers_422(
    customer_flow: CustomerFlowHarness, budget_body: dict[str, object]
) -> None:
    """The customer must confirm it, and money is a positive JSON integer of paise."""
    session = customer_flow.open_customer_session()
    response = customer_flow.api.client.put(
        session.base_path + "/budget", json=budget_body, headers=session.headers
    )
    assert_problem(response, 422, "REQUEST_VALIDATION_FAILED")


@pytest.mark.parametrize(
    "send_request",
    [
        lambda session: session.find_alternatives("offer-not-quoted"),
        lambda session: session.explain("offer-not-quoted"),
    ],
    ids=["alternatives", "explanation"],
)
def test_an_offer_not_quoted_for_the_item_answers_404(
    customer_flow: CustomerFlowHarness,
    send_request: Callable[[CustomerSessionClient], httpx.Response],
) -> None:
    """Alternatives and explanations exist only for plans quoted for the session's item."""
    session = customer_flow.open_customer_session()
    session.confirm_budget()
    assert_problem(send_request(session), 404, "OFFER_NOT_FOUND")
