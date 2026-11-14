"""Report endpoints on the test database: shop-scoped aggregates, empty shapes, idempotent send."""

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import Connection, text

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.sale_api_helpers import (
    COUNTER_PATH,
    PHONE_128_GB_ID,
    TwoShops,
    agree_to_offer_in_the_service,
    start_sale,
)

pytestmark = pytest.mark.integration

REPORTS_PATH = "/api/v1/reports"
FIRST_SHOP_MERCHANT_ID = "01JCMERCHANTSALES000000001"
CURRENT_WEEK_MONDAY = "2026-11-09"
EMPTY_BUCKET_SHAPE = {"areBudgetBucketsHidden": True, "budgetBuckets": []}


def _read(harness: ApiHarness, path: str, headers: dict[str, str]) -> dict[str, Any]:
    """Reads one report and gives its 200 body."""
    response = harness.client.get(f"{REPORTS_PATH}{path}", headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _tell_budget_and_view_plans(harness: ApiHarness, sale_id: str, budget_in_rupees: str) -> None:
    """Appends the two customer steps Layer 3 will record: a budget, then the plans seen."""
    with SqlAlchemyUnitOfWork(harness.session_factory, harness.clock) as unit_of_work:
        for stage, budget in (
            (FunnelStage.BUDGET_TOLD, Money.from_rupees(budget_in_rupees)),
            (FunnelStage.PLANS_VIEWED, None),
        ):
            unit_of_work.funnel_events.append(
                FunnelEvent(
                    id=f"R{sale_id[-19:]}{stage.value[:6]}",
                    sale_id=sale_id,
                    merchant_id=FIRST_SHOP_MERCHANT_ID,
                    stage=stage,
                    occurred_at=harness.clock.now(),
                    monthly_budget=budget,
                )
            )


def _store_week(harness: ApiHarness, gateway: MockPaymentGatewayAdapter, shops: TwoShops) -> None:
    """Six 128 GB sales with budgets ₹2,400 to ₹2,950 never agreed, one agreed at ₹3,800.

    The six are then left past the choosing lifetime and the counter list records their expiry,
    so all seven are finished sales the reports may count.
    """
    for budget_in_rupees in ("2400", "2600", "2700", "2800", "2900", "2950", "3800"):
        sale_id = start_sale(harness, shops.first_shop_headers, PHONE_128_GB_ID)["saleId"]
        _tell_budget_and_view_plans(harness, sale_id, budget_in_rupees)
    agree_to_offer_in_the_service(harness, gateway, sale_id)
    _expire_choosing_sales(harness, shops.first_shop_headers)


def _expire_choosing_sales(harness: ApiHarness, headers: dict[str, str]) -> None:
    """Moves the clock past the choosing lifetime and reads the counter list, which expires them."""
    harness.clock.advance(timedelta(seconds=ApplicationSettings().sale_choosing_expiry_in_seconds))
    assert harness.client.get(COUNTER_PATH, headers=headers).status_code == 200


def test_report_endpoints_need_the_merchant_token(mock_api: ApiHarness) -> None:
    """No bearer token, no report."""
    for path in ("/funnel?range=TODAY", "/money-due", "/weekly-message"):
        response = mock_api.client.get(f"{REPORTS_PATH}{path}")
        assert response.status_code == 401
        assert response.json()["code"] == "MERCHANT_AUTHENTICATION_REQUIRED"


def test_a_range_is_required_and_must_be_known(mock_api: ApiHarness, shops: TwoShops) -> None:
    """The range must be TODAY, THIS_WEEK or THIS_MONTH."""
    for query in ("", "?range=YESTERDAY"):
        response = mock_api.client.get(
            f"{REPORTS_PATH}/funnel{query}", headers=shops.first_shop_headers
        )
        assert response.status_code == 422
        assert response.json()["fieldErrors"][0]["field"] == "range"


def test_an_empty_shop_gets_the_empty_shapes(mock_api: ApiHarness, shops: TwoShops) -> None:
    """Zeros, no drop, hidden buckets, no actions, nothing due and a "no sales yet" message."""
    headers = shops.first_shop_headers
    funnel = _read(mock_api, "/funnel?range=THIS_WEEK", headers)
    missed = _read(mock_api, "/missed-sales?range=THIS_WEEK", headers)
    actions = _read(mock_api, "/suggested-actions?range=THIS_WEEK", headers)
    money_due = _read(mock_api, "/money-due", headers)
    message = _read(mock_api, "/weekly-message", headers)
    assert [stage["customerCount"] for stage in funnel["stages"]] == [0, 0, 0, 0, 0]
    assert funnel["biggestDrop"] is None
    assert (funnel["periodStartDate"], funnel["periodEndDate"]) == (
        CURRENT_WEEK_MONDAY,
        "2026-11-15",
    )
    assert missed == {
        "range": "THIS_WEEK",
        "periodStartDate": CURRENT_WEEK_MONDAY,
        "periodEndDate": "2026-11-15",
        "missedCustomerCount": 0,
        "isSuppressed": False,
        "budgetCeilingInPaise": None,
        "productInsight": None,
        "budgetTotalCustomerCount": 0,
        **EMPTY_BUCKET_SHAPE,
    }
    assert actions == {"actions": []}
    assert money_due == {"totalDueInPaise": 0, "nextExpectedDate": None, "batches": []}
    assert message["messages"]["en"]["paragraphs"] == ["No EMI sales this week yet."]
    assert (message["isSent"], message["sentAt"], message["source"]) == (False, None, "TEMPLATE")


def test_report_counts_equal_independent_count_queries_and_stay_in_their_shop(
    mock_api: ApiHarness,
    mock_gateway: MockPaymentGatewayAdapter,
    shops: TwoShops,
    database_connection: Connection,
) -> None:
    """The funnel equals a plain COUNT per stage; the other shop sees none of it."""
    _store_week(mock_api, mock_gateway, shops)
    funnel = _read(mock_api, "/funnel?range=TODAY", shops.first_shop_headers)
    independent_counts: dict[str, int] = dict(
        database_connection.execute(
            text(
                "SELECT f.stage, count(*) FROM funnel_event f JOIN sale s ON s.id = f.sale_id"
                " WHERE s.merchant_id = :merchant_id AND s.status <> 'CHOOSING'"
                " GROUP BY f.stage"
            ),
            {"merchant_id": FIRST_SHOP_MERCHANT_ID},
        ).all()
    )
    assert {stage["stage"]: stage["customerCount"] for stage in funnel["stages"]} == {
        "STARTED": independent_counts["STARTED"],
        "BUDGET_TOLD": independent_counts["BUDGET_TOLD"],
        "PLANS_VIEWED": independent_counts["PLANS_VIEWED"],
        "AGREED": None,
        "PAID": None,
    }
    assert independent_counts["STARTED"] == 7
    other_shop = _read(mock_api, "/funnel?range=TODAY", shops.second_shop_headers)
    assert [stage["customerCount"] for stage in other_shop["stages"]] == [0, 0, 0, 0, 0]
    other_missed = _read(mock_api, "/missed-sales?range=TODAY", shops.second_shop_headers)
    assert other_missed["missedCustomerCount"] == 0


def test_missed_sales_and_actions_come_from_the_quoted_plans(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter, shops: TwoShops
) -> None:
    """Six missed under ₹3,000 on the 128 GB phone; the 9/12-month and 64 GB suggestions."""
    _store_week(mock_api, mock_gateway, shops)
    missed = _read(mock_api, "/missed-sales?range=THIS_MONTH", shops.first_shop_headers)
    actions = _read(mock_api, "/suggested-actions?range=THIS_MONTH", shops.first_shop_headers)
    assert (missed["missedCustomerCount"], missed["budgetCeilingInPaise"]) == (6, 300_000)
    assert missed["productInsight"]["lowestNoExtraCostMonthlyInPaise"] == 366_667
    assert missed["productInsight"]["cheapestPlanUnderCeiling"] == {
        "monthlyInstallmentInPaise": 205_000,
        "extraInTotalInPaise": 260_000,
    }
    assert [bucket["customerCount"] for bucket in missed["budgetBuckets"]] == [None, 5, 0, None, 0]
    assert [action["actionCode"] for action in actions["actions"]] == [
        "ASK_BRAND_FOR_LONGER_NO_COST_PLAN",
        "KEEP_CHEAPER_MODEL_READY",
    ]
    assert actions["actions"][0]["parameters"]["suggestedTenures"] == [
        {"tenureInMonths": 9, "monthlyInstallmentInPaise": 244_444},
        {"tenureInMonths": 12, "monthlyInstallmentInPaise": 183_333},
    ]


def test_one_customer_still_choosing_today_shows_in_no_report_until_the_sale_ends(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """Rule 6: a live customer who told ₹2,400 and saw the plans is in no report at all.

    Once the sale expires it joins the cohort, still as "fewer than 5" with nothing derived.
    """
    headers = shops.first_shop_headers
    sale_id = start_sale(mock_api, headers, PHONE_128_GB_ID)["saleId"]
    _tell_budget_and_view_plans(mock_api, sale_id, "2400")
    for reporting_range in ("TODAY", "THIS_WEEK"):
        funnel = _read(mock_api, f"/funnel?range={reporting_range}", headers)
        missed = _read(mock_api, f"/missed-sales?range={reporting_range}", headers)
        actions = _read(mock_api, f"/suggested-actions?range={reporting_range}", headers)
        assert [stage["customerCount"] for stage in funnel["stages"]] == [0, 0, 0, 0, 0]
        assert funnel["biggestDrop"] is None
        assert (missed["missedCustomerCount"], missed["budgetTotalCustomerCount"]) == (0, 0)
        assert (missed["budgetCeilingInPaise"], missed["productInsight"]) == (None, None)
        assert actions == {"actions": []}
    message = _read(mock_api, "/weekly-message", headers)
    assert message["messages"]["en"]["paragraphs"] == ["No EMI sales this week yet."]
    _expire_choosing_sales(mock_api, headers)
    funnel = _read(mock_api, "/funnel?range=TODAY", headers)
    missed = _read(mock_api, "/missed-sales?range=TODAY", headers)
    assert [stage["isSuppressed"] for stage in funnel["stages"]] == [True] * 5
    assert funnel["biggestDrop"] is None
    assert (missed["isSuppressed"], missed["budgetCeilingInPaise"], missed["productInsight"]) == (
        True,
        None,
        None,
    )
    assert missed["budgetTotalCustomerCount"] is None
    assert _read(mock_api, "/suggested-actions?range=TODAY", headers) == {"actions": []}


def test_a_few_finished_sales_without_budgets_show_no_zero_the_funnel_hides(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """Two expired sales and no budget: the funnel hides BUDGET_TOLD, so the card hides its 0s.

    A budget total or missed count of 0 would tell the merchant those two never told a budget.
    """
    headers = shops.first_shop_headers
    for _ in range(2):
        start_sale(mock_api, headers, PHONE_128_GB_ID)
    _expire_choosing_sales(mock_api, headers)
    funnel = _read(mock_api, "/funnel?range=TODAY", headers)
    missed = _read(mock_api, "/missed-sales?range=TODAY", headers)
    assert [stage["customerCount"] for stage in funnel["stages"]] == [None] * 5
    assert {
        field: missed[field]
        for field in (
            "missedCustomerCount",
            "isSuppressed",
            "budgetTotalCustomerCount",
            "areBudgetBucketsHidden",
            "budgetBuckets",
        )
    } == {
        "missedCustomerCount": None,
        "isSuppressed": True,
        "budgetTotalCustomerCount": None,
        **EMPTY_BUCKET_SHAPE,
    }


def test_sending_the_weekly_message_is_idempotent(mock_api: ApiHarness, shops: TwoShops) -> None:
    """A repeat send answers 200 with the first sentAt; another shop stays unsent."""
    send_path = f"{REPORTS_PATH}/weekly-message/send"
    body = {"periodStartDate": CURRENT_WEEK_MONDAY}
    first = mock_api.client.post(send_path, json=body, headers=shops.first_shop_headers)
    second = mock_api.client.post(send_path, json=body, headers=shops.first_shop_headers)
    read_back = _read(
        mock_api, f"/weekly-message?periodStartDate={CURRENT_WEEK_MONDAY}", shops.first_shop_headers
    )
    other_shop = _read(mock_api, "/weekly-message", shops.second_shop_headers)
    assert (first.status_code, second.status_code) == (200, 200)
    assert first.json()["isSent"] is True
    assert first.json()["sentAt"] == second.json()["sentAt"] == read_back["sentAt"]
    assert other_shop["isSent"] is False


@pytest.mark.parametrize("period_start_date", ["2026-11-10", "2026-11-16"])
def test_a_week_that_is_not_a_monday_or_not_started_is_refused(
    mock_api: ApiHarness, shops: TwoShops, period_start_date: str
) -> None:
    """422 INVALID_REPORTING_PERIOD, for reading and for sending."""
    read = mock_api.client.get(
        f"{REPORTS_PATH}/weekly-message?periodStartDate={period_start_date}",
        headers=shops.first_shop_headers,
    )
    sent = mock_api.client.post(
        f"{REPORTS_PATH}/weekly-message/send",
        json={"periodStartDate": period_start_date},
        headers=shops.first_shop_headers,
    )
    assert (read.status_code, sent.status_code) == (422, 422)
    assert read.json()["code"] == sent.json()["code"] == "INVALID_REPORTING_PERIOD"
