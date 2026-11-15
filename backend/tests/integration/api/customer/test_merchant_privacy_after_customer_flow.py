"""Cross-layer privacy (CLAUDE.md rule 6): after a full customer flow, the shop learns nothing more.

The customer confirms ₹3,000 and allows the comfort check (inflow ₹30,000, existing EMIs ₹8,000,
ratios 3,889 / 3,950 / 3,350 bp). Then every merchant endpoint that can mention the sale is
read, the live status stream included, and none of those figures or words may appear: only the
status, the chosen plan and totals, and aggregates.
"""

import asyncio
import json
import re
from typing import Any

import httpx
import pytest

from tests.integration.api.asgi_event_stream import AsgiEventStream
from tests.integration.api.customer.customer_api_helpers import CustomerFlowHarness
from tests.integration.api.customer.test_customer_flow_end_to_end import (
    PLAN_A_AS_THE_MERCHANT_SEES_IT,
    run_design_customer_flow,
)
from tests.integration.api.sale_api_helpers import COUNTER_PATH, SALES_PATH

pytestmark = pytest.mark.integration

CUSTOMER_ONLY_AMOUNTS_IN_PAISE = (3_000_000, 800_000, 300_000)
"""Inflow ₹30,000, existing EMIs ₹8,000 and the customer's own ₹3,000 budget."""
CUSTOMER_ONLY_BASIS_POINTS = (3889, 3950, 3350, 2667, 1222, 1283, 683, 3667)
"""The comfort ratios and shares the customer was shown on C4 to C6."""
BANNED_WORDS_IN_ANY_MERCHANT_RESPONSE = (
    "income",
    "inflow",
    "comfort",
    "ratio",
    "basispoints",
    "comfortable",
    "stretching",
    "risky",
    "phonelasttwodigits",
    "9000000042",
    "progress",
    "scanned",
)
BANNED_WORDS_IN_PER_SALE_RESPONSES = (
    "budget",
    "step",
    "plans_viewed",
    "budget_told",
    "explanation",
)
"""Per sale, even a funnel stage name would show one customer's progress."""
MERCHANT_SALE_STATUSES = {"CHOOSING", "READY_TO_PAY"}


def find_privacy_leaks(serialized_text: str, banned_words: tuple[str, ...]) -> list[str]:
    """Lists every customer-only number (as a whole number) and banned word found in the text."""
    lowered_text = serialized_text.lower()
    leaks = [word for word in banned_words if word in lowered_text]
    leaks.extend(
        str(number)
        for number in (*CUSTOMER_ONLY_AMOUNTS_IN_PAISE, *CUSTOMER_ONLY_BASIS_POINTS)
        if re.search(rf"(?<![0-9]){number}(?![0-9])", serialized_text)
    )
    return leaks


def read_ok(response: httpx.Response) -> Any:  # noqa: ANN401 - any JSON body
    """Requires a 200 and gives the body."""
    assert response.status_code == 200, response.text
    return response.json()


def read_merchant_views(customer_flow: CustomerFlowHarness, sale_id: str) -> dict[str, Any]:
    """Reads every merchant response that can mention the sale, keyed by what it is."""
    client, headers = customer_flow.api.client, customer_flow.merchant_headers
    per_sale = {
        "sale detail": read_ok(client.get(f"{SALES_PATH}/{sale_id}", headers=headers)),
        "counter list": read_ok(client.get(COUNTER_PATH, headers=headers)),
        "hand-off": read_ok(client.get(f"{SALES_PATH}/{sale_id}/handoff", headers=headers)),
    }
    reports = {
        f"report {path}": read_ok(client.get(f"/api/v1/reports/{path}", headers=headers))
        for path in (
            "funnel?range=THIS_WEEK",
            "missed-sales?range=THIS_WEEK",
            "suggested-actions?range=THIS_WEEK",
            "money-due",
            "weekly-message",
        )
    }
    return {"per sale": per_sale, "reports": reports}


def test_merchant_responses_after_the_customer_flow_hold_no_customer_detail(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Sale, counter list, hand-off and every report: no income, EMIs, ratios, budget or steps."""
    sale_body, _, _ = run_design_customer_flow(customer_flow)
    views = read_merchant_views(customer_flow, sale_body["saleId"])
    for name, body in views["per sale"].items():
        leaks = find_privacy_leaks(
            json.dumps(body),
            BANNED_WORDS_IN_ANY_MERCHANT_RESPONSE + BANNED_WORDS_IN_PER_SALE_RESPONSES,
        )
        assert leaks == [], f"{name} shows customer detail: {leaks}"
    for name, body in views["reports"].items():
        leaks = find_privacy_leaks(json.dumps(body), BANNED_WORDS_IN_ANY_MERCHANT_RESPONSE)
        assert leaks == [], f"{name} shows customer detail: {leaks}"


def test_the_merchant_sees_only_the_status_and_the_chosen_plan_of_the_sale(
    customer_flow: CustomerFlowHarness,
) -> None:
    """READY_TO_PAY with plan A's monthly, extra and total, in the detail and the counter list."""
    sale_body, _, _ = run_design_customer_flow(customer_flow)
    views = read_merchant_views(customer_flow, sale_body["saleId"])["per sale"]
    (counter_sale,) = [
        sale for sale in views["counter list"]["sales"] if sale["saleId"] == sale_body["saleId"]
    ]
    for merchant_view in (views["sale detail"], counter_sale, views["hand-off"]["sale"]):
        assert merchant_view["status"] == "READY_TO_PAY"
        assert merchant_view["chosenPlan"] == PLAN_A_AS_THE_MERCHANT_SEES_IT


def test_the_live_status_stream_carries_only_choosing_then_ready_to_pay(
    customer_flow: CustomerFlowHarness,
) -> None:
    """The shop's stream hears the sale start and the agreement, and no customer step between."""

    async def scenario() -> list[str]:
        """Opens the shop's stream, plays the customer flow beside it and reads the two events."""
        stream = AsgiEventStream(
            customer_flow.api.client.app,
            f"{SALES_PATH}/events",
            customer_flow.merchant_headers,
        )
        await stream.open()
        await asyncio.to_thread(run_design_customer_flow, customer_flow)
        frames = [await stream.read_frame_other_than_heartbeat() for _ in range(2)]
        await stream.close()
        return [frame for frame in frames if frame is not None]

    frames = asyncio.run(scenario())
    payloads = [json.loads(frame.split("\n")[1].removeprefix("data: ")) for frame in frames]
    assert [payload["status"] for payload in payloads] == ["CHOOSING", "READY_TO_PAY"]
    assert all(set(payload) == {"saleId", "status", "statusChangedAt"} for payload in payloads)
    assert {payload["status"] for payload in payloads} <= MERCHANT_SALE_STATUSES
    leaks = find_privacy_leaks(
        "\n".join(frames),
        BANNED_WORDS_IN_ANY_MERCHANT_RESPONSE + BANNED_WORDS_IN_PER_SALE_RESPONSES,
    )
    assert leaks == []


@pytest.mark.parametrize(
    ("text", "expected_leaks"),
    [
        ('{"monthlyInPaise": 300000}', ["300000"]),
        ('{"priceInPaise": 1800000}', []),
        ('{"band": "STRETCHING"}', ["stretching"]),
        ('{"ratio": 3889}', ["ratio", "3889"]),
    ],
)
def test_find_privacy_leaks_matches_whole_numbers_and_any_casing(
    text: str, expected_leaks: list[str]
) -> None:
    """₹18,000 (1800000 paise) is not ₹8,000 (800000); words match whatever their case."""
    assert find_privacy_leaks(text, BANNED_WORDS_IN_ANY_MERCHANT_RESPONSE) == expected_leaks
