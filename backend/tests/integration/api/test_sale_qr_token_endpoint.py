"""POST /api/v1/sales/{saleId}/qr-tokens and the agreed plan on the counter list."""

from datetime import timedelta

import pytest

from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.sale_api_helpers import (
    COUNTER_PATH,
    SALES_PATH,
    TwoShops,
    mark_ready_to_pay_in_the_database,
    start_sale,
)

pytestmark = pytest.mark.integration


def test_post_qr_tokens_issues_a_new_qr_while_choosing(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """201 with the URL and expiry only, a different token, Location and no-store."""
    started = start_sale(mock_api, shops.first_shop_headers)
    mock_api.clock.advance(timedelta(minutes=10))
    response = mock_api.client.post(
        f"{SALES_PATH}/{started['saleId']}/qr-tokens", headers=shops.first_shop_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"customerUrl", "expiresAt"}
    assert body["customerUrl"] != started["qr"]["customerUrl"]
    assert body["expiresAt"] == "2026-11-14T10:55:00Z"
    assert response.headers["Location"] == f"{SALES_PATH}/{started['saleId']}"
    assert response.headers["Cache-Control"] == "no-store"


def test_post_qr_tokens_after_agreement_answers_409_and_for_another_shop_404(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """Once the customer agreed no new QR code exists; another shop cannot even find the sale."""
    started = start_sale(mock_api, shops.first_shop_headers)
    qr_path = f"{SALES_PATH}/{started['saleId']}/qr-tokens"
    other_response = mock_api.client.post(qr_path, headers=shops.second_shop_headers)
    mark_ready_to_pay_in_the_database(mock_api, str(started["saleId"]))
    conflict_response = mock_api.client.post(qr_path, headers=shops.first_shop_headers)
    assert (other_response.status_code, other_response.json()["code"]) == (404, "SALE_NOT_FOUND")
    assert conflict_response.status_code == 409
    assert conflict_response.json()["code"] == "SALE_STATE_CONFLICT"


def test_agreed_sale_shows_its_chosen_plan_as_shown_to_the_customer(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """READY_TO_PAY with plan A in integer paise: 6 x 366,667, nothing extra, 22,00,000 total."""
    started = start_sale(mock_api, shops.first_shop_headers)
    mark_ready_to_pay_in_the_database(mock_api, str(started["saleId"]))
    (listed_sale,) = mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers).json()[
        "sales"
    ]
    assert listed_sale["status"] == "READY_TO_PAY"
    assert listed_sale["chosenPlan"] == {
        "offerId": "offer-plan-a",
        "planKind": "NO_COST",
        "lenderLabel": "Brand",
        "tenureInMonths": 6,
        "monthlyInstallmentInPaise": 366_667,
        "extraInTotalInPaise": 0,
        "totalPayableInPaise": 2_200_000,
    }
