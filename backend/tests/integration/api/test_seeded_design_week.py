"""The seeded demo week, read through the API, equals every DESIGN_SPEC section 4 number."""

from datetime import timedelta
from functools import partial
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.services.demo_report_history_seed_service import DemoReportHistorySeedService
from scripts.demo_report_history import DEMO_REPORT_HISTORY
from scripts.seed_demo_data import seed_demo_merchant
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.integration.api.api_harness import ApiHarness

pytestmark = pytest.mark.integration

SYNTHETIC_PIN = "135790"
REPORTS_PATH = "/api/v1/reports"


def _seed_and_pair(mock_api: ApiHarness, gateway: MockPaymentGatewayAdapter) -> dict[str, str]:
    """Runs the shop step, the history step twice, then pairs RAVI-0193."""
    unit_of_work_factory = partial(SqlAlchemyUnitOfWork, mock_api.session_factory, mock_api.clock)
    seed_demo_merchant(unit_of_work_factory, SYNTHETIC_PIN)
    service = DemoReportHistorySeedService(
        unit_of_work_factory=unit_of_work_factory,
        payment_gateway=gateway,
        clock=mock_api.clock,
        id_generator=SequentialIdGenerator("01JCSEEDHISTORY"),
        time_zone=ZoneInfo("Asia/Kolkata"),
        choosing_lifetime=timedelta(hours=1),
    )
    assert service.seed("RAVI-0193", DEMO_REPORT_HISTORY).added_sale_count == 120
    assert service.seed("RAVI-0193", DEMO_REPORT_HISTORY).added_sale_count == 0
    pairing = mock_api.client.post(
        "/api/v1/merchants/pairing", json={"shopId": "RAVI-0193", "pin": SYNTHETIC_PIN}
    )
    return {"Authorization": f"Bearer {pairing.json()['accessToken']}"}


def _read(mock_api: ApiHarness, path: str, headers: dict[str, str]) -> dict[str, Any]:
    """Reads one endpoint and gives its 200 body."""
    response = mock_api.client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


@pytest.fixture
def demo_headers(mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter) -> dict[str, str]:
    """The seeded demo shop, paired."""
    return _seed_and_pair(mock_api, mock_gateway)


def test_seeded_week_funnel_is_120_96_88_51_44_with_37_lost_after_the_plans(
    mock_api: ApiHarness, demo_headers: dict[str, str]
) -> None:
    """DESIGN_SPEC funnel, read twice-seeded (no duplicates)."""
    funnel = _read(mock_api, f"{REPORTS_PATH}/funnel?range=THIS_WEEK", demo_headers)
    assert [(stage["stage"], stage["customerCount"]) for stage in funnel["stages"]] == [
        ("STARTED", 120),
        ("BUDGET_TOLD", 96),
        ("PLANS_VIEWED", 88),
        ("AGREED", 51),
        ("PAID", 44),
    ]
    assert funnel["biggestDrop"] == {
        "afterStage": "PLANS_VIEWED",
        "customerCount": 37,
        "isSuppressed": False,
    }


def test_seeded_week_missed_sales_are_12_under_3000_on_the_128_gb_phone(
    mock_api: ApiHarness, demo_headers: dict[str, str]
) -> None:
    """Buckets 5, 7, 14, 21, 49 (96); ₹3,667 lowest no-cost; ₹2,050 plan adds ₹2,600."""
    missed = _read(mock_api, f"{REPORTS_PATH}/missed-sales?range=THIS_WEEK", demo_headers)
    assert (missed["missedCustomerCount"], missed["budgetCeilingInPaise"]) == (12, 300_000)
    assert missed["productInsight"]["productName"] == "Example phone, 128 GB"
    assert missed["productInsight"]["lowestNoExtraCostMonthlyInPaise"] == 366_667
    assert missed["productInsight"]["cheapestPlanUnderCeiling"] == {
        "monthlyInstallmentInPaise": 205_000,
        "extraInTotalInPaise": 260_000,
    }
    assert missed["budgetTotalCustomerCount"] == 96
    assert [bucket["customerCount"] for bucket in missed["budgetBuckets"]] == [5, 7, 14, 21, 49]
    assert [bucket["isUnderCeiling"] for bucket in missed["budgetBuckets"]] == [
        True,
        True,
        False,
        False,
        False,
    ]
    assert [
        [plan["monthlyInstallmentInPaise"] for plan in bucket["plans"]]
        for bucket in missed["budgetBuckets"]
    ] == [[205_000], [], [], [366_667, 385_000], []]


def test_seeded_week_suggests_9_and_12_month_no_cost_and_the_64_gb_phone(
    mock_api: ApiHarness, demo_headers: dict[str, str]
) -> None:
    """The two M5 tips with computed figures."""
    actions = _read(mock_api, f"{REPORTS_PATH}/suggested-actions?range=THIS_WEEK", demo_headers)
    longer, cheaper = actions["actions"]
    assert longer["actionCode"] == "ASK_BRAND_FOR_LONGER_NO_COST_PLAN"
    assert longer["parameters"]["currentNoCostTenureInMonths"] == 6
    assert longer["parameters"]["suggestedTenures"] == [
        {"tenureInMonths": 9, "monthlyInstallmentInPaise": 244_444},
        {"tenureInMonths": 12, "monthlyInstallmentInPaise": 183_333},
    ]
    assert (
        longer["parameters"]["missedCustomerCount"],
        longer["parameters"]["budgetCeilingInPaise"],
    ) == (12, 300_000)
    assert cheaper["actionCode"] == "KEEP_CHEAPER_MODEL_READY"
    assert cheaper["parameters"] | {"productId": None} == {
        "productId": None,
        "productName": "Example phone, 64 GB",
        "listPriceInPaise": 1_800_000,
        "monthlyInstallmentInPaise": 300_000,
        "tenureInMonths": 6,
    }


def test_seeded_shop_has_1_84_000_due_and_the_design_weekly_message(
    mock_api: ApiHarness, demo_headers: dict[str, str]
) -> None:
    """Money due and the English message, every number from the reports."""
    money_due = _read(mock_api, f"{REPORTS_PATH}/money-due", demo_headers)
    message = _read(mock_api, f"{REPORTS_PATH}/weekly-message", demo_headers)
    assert (money_due["totalDueInPaise"], money_due["nextExpectedDate"]) == (
        18_400_000,
        "2027-01-13",
    )
    assert message["messages"]["en"]["paragraphs"] == [
        "44 of 120 customers bought on EMI. The biggest drop was after seeing the plans.",
        "12 customers wanted under ₹3,000 a month with nothing extra, and no plan fit. "
        "₹1,84,000 is due from brands, first payment around 13 Jan.",
        "One thing to do: ask the brand for a 9 or 12-month no-cost plan on Example phone, "
        "128 GB. That would be ₹2,444 or ₹1,833 a month.",
    ]


def test_seeded_counter_list_shows_todays_three_m2_sales(
    mock_api: ApiHarness, demo_headers: dict[str, str]
) -> None:
    """4821 choosing, 4817 ready to pay on the 64 GB no-cost plan, 4812 paid; newest first."""
    counter = _read(mock_api, "/api/v1/sales?view=counter", demo_headers)
    assert [
        (sale["sessionCode"], sale["status"], sale["productName"]) for sale in counter["sales"]
    ] == [
        ("4821", "CHOOSING", "Example phone, 128 GB"),
        ("4817", "READY_TO_PAY", "Example phone, 64 GB"),
        ("4812", "PAID", "Example earbuds"),
    ]
    assert counter["sales"][1]["chosenPlan"]["planKind"] == "NO_COST"
    today = _read(mock_api, f"{REPORTS_PATH}/funnel?range=TODAY", demo_headers)
    assert today["stages"][0] == {"stage": "STARTED", "customerCount": None, "isSuppressed": True}
