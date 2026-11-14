"""The sale endpoints on PostgreSQL with the Mock gateway: shapes, auth, scoping and replay."""

from datetime import UTC, datetime, timedelta

import pytest

from emi_copilot.domain.sales import SaleStatus
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.sale_api_helpers import (
    COUNTER_PATH,
    PHONE_64_GB_ID,
    PHONE_128_GB_ID,
    QR_EXPIRES_AT,
    SALE_DETAIL_KEYS,
    SALES_PATH,
    SECOND_SHOP_PHONE_ID,
    TwoShops,
    start_sale,
)

pytestmark = pytest.mark.integration


def test_post_sales_starts_a_choosing_sale_with_a_qr_url_location_and_no_store(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """201 with exactly the detail keys, the list price, a 4-digit code and a fragment URL."""
    response = mock_api.client.post(
        SALES_PATH, json={"productId": PHONE_128_GB_ID}, headers=shops.first_shop_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body) == SALE_DETAIL_KEYS
    assert body["status"] == "CHOOSING"
    assert body["priceInPaise"] == 2_200_000
    assert body["productName"] == "Example phone, 128 GB"
    assert body["chosenPlan"] is None
    assert len(body["sessionCode"]) == 4
    assert body["sessionCode"].isdigit()
    assert body["startedAt"] == body["statusChangedAt"] == "2026-11-14T10:30:00Z"
    assert body["qr"]["customerUrl"].startswith("http://localhost:5174/#t=")
    assert body["qr"]["expiresAt"] == QR_EXPIRES_AT.isoformat().replace("+00:00", "Z")
    assert response.headers["Location"] == f"{SALES_PATH}/{body['saleId']}"
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    ("body", "expected_status"),
    [
        ({"productId": SECOND_SHOP_PHONE_ID}, 404),
        ({"productId": "01JCPRODUCT000000000000099"}, 404),
        ({"productId": PHONE_128_GB_ID, "priceInPaise": 100}, 422),
        ({}, 422),
    ],
    ids=["another-shops-product", "unknown-product", "price-in-body", "no-product"],
)
def test_post_sales_refuses_another_shops_product_and_any_price_in_the_body(
    mock_api: ApiHarness, shops: TwoShops, body: dict[str, object], expected_status: int
) -> None:
    """The price comes from the catalogue only; another shop's product is simply not found."""
    response = mock_api.client.post(SALES_PATH, json=body, headers=shops.first_shop_headers)
    assert response.status_code == expected_status
    assert response.headers["Content-Type"] == "application/problem+json"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", SALES_PATH),
        ("GET", COUNTER_PATH),
        ("GET", f"{SALES_PATH}/01JCSALE000000000000000001"),
        ("POST", f"{SALES_PATH}/01JCSALE000000000000000001/qr-tokens"),
    ],
)
def test_sale_endpoints_without_a_bearer_token_answer_401(
    mock_api: ApiHarness, method: str, path: str
) -> None:
    """Every sale endpoint needs the merchant's device token."""
    response = mock_api.client.request(method, path, json={"productId": PHONE_128_GB_ID})
    assert response.status_code == 401
    assert response.json()["code"] == "MERCHANT_AUTHENTICATION_REQUIRED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_idempotency_key_replay_returns_the_same_sale_without_a_qr(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """Same key and body: the same sale, qr null; one sale only is on the counter."""
    headers = {**shops.first_shop_headers, "Idempotency-Key": "sale-start-key-0001"}
    first = mock_api.client.post(SALES_PATH, json={"productId": PHONE_128_GB_ID}, headers=headers)
    replay = mock_api.client.post(SALES_PATH, json={"productId": PHONE_128_GB_ID}, headers=headers)
    assert (first.status_code, replay.status_code) == (201, 201)
    assert replay.json() == {**first.json(), "qr": None}
    assert replay.headers["Location"] == first.headers["Location"]
    counter = mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers).json()
    assert len(counter["sales"]) == 1


def test_idempotency_key_with_another_body_answers_422(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """Same key, another product: IDEMPOTENCY_KEY_REUSED (api-conventions section 5)."""
    headers = {**shops.first_shop_headers, "Idempotency-Key": "sale-start-key-0001"}
    mock_api.client.post(SALES_PATH, json={"productId": PHONE_128_GB_ID}, headers=headers)
    response = mock_api.client.post(SALES_PATH, json={"productId": PHONE_64_GB_ID}, headers=headers)
    assert response.status_code == 422
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_too_short_idempotency_key_answers_422(mock_api: ApiHarness, shops: TwoShops) -> None:
    """A key is 8 to 255 visible ASCII characters."""
    response = mock_api.client.post(
        SALES_PATH,
        json={"productId": PHONE_128_GB_ID},
        headers={**shops.first_shop_headers, "Idempotency-Key": "short"},
    )
    assert response.status_code == 422
    assert response.json()["fieldErrors"][0]["field"] == "Idempotency-Key"


def test_counter_list_is_newest_first_and_only_the_shops_own(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """Two sales of the first shop, newest first; the second shop's list is its own."""
    older = start_sale(mock_api, shops.first_shop_headers)
    mock_api.clock.advance(timedelta(minutes=1))
    newer = start_sale(mock_api, shops.first_shop_headers, PHONE_64_GB_ID)
    start_sale(mock_api, shops.second_shop_headers, SECOND_SHOP_PHONE_ID)
    response = mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers)
    assert response.status_code == 200
    listed_ids = [sale["saleId"] for sale in response.json()["sales"]]
    assert listed_ids == [newer["saleId"], older["saleId"]]
    assert older["sessionCode"] != newer["sessionCode"]


@pytest.mark.parametrize("query", ["", "?view=report"])
def test_sales_list_without_the_counter_view_answers_422(
    mock_api: ApiHarness, shops: TwoShops, query: str
) -> None:
    """view=counter is required; no other view exists yet."""
    response = mock_api.client.get(f"{SALES_PATH}{query}", headers=shops.first_shop_headers)
    assert response.status_code == 422


def test_counter_list_starts_afresh_at_ist_midnight(mock_api: ApiHarness, shops: TwoShops) -> None:
    """A sale at 23:59 IST is not on the list two minutes later, at 00:01 IST."""
    mock_api.clock.advance(datetime(2026, 11, 14, 18, 29, tzinfo=UTC) - mock_api.clock.now())
    start_sale(mock_api, shops.first_shop_headers)
    assert (
        len(mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers).json()["sales"])
        == 1
    )
    mock_api.clock.advance(timedelta(minutes=2))
    after_midnight = start_sale(mock_api, shops.first_shop_headers, PHONE_64_GB_ID)
    listed = mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers).json()["sales"]
    assert [sale["saleId"] for sale in listed] == [after_midnight["saleId"]]


def test_get_sale_gives_the_detail_with_qr_null_and_hides_other_shops_sales(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """The owner reads it without a QR (tokens aren't stored); another shop gets 404."""
    started = start_sale(mock_api, shops.first_shop_headers)
    sale_path = f"{SALES_PATH}/{started['saleId']}"
    own_response = mock_api.client.get(sale_path, headers=shops.first_shop_headers)
    other_response = mock_api.client.get(sale_path, headers=shops.second_shop_headers)
    unknown_response = mock_api.client.get(
        f"{SALES_PATH}/01JCSALE000000000000000099", headers=shops.first_shop_headers
    )
    assert own_response.status_code == 200
    assert own_response.json() == {**started, "qr": None}
    assert (other_response.status_code, other_response.json()["code"]) == (404, "SALE_NOT_FOUND")
    assert unknown_response.status_code == 404


def test_sale_still_choosing_after_an_hour_reads_expired_and_leaves_the_list(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """At exactly 3600 s the sale is EXPIRED, dated at its deadline."""
    started = start_sale(mock_api, shops.first_shop_headers)
    mock_api.clock.advance(timedelta(hours=1))
    detail = mock_api.client.get(
        f"{SALES_PATH}/{started['saleId']}", headers=shops.first_shop_headers
    ).json()
    assert detail["status"] == SaleStatus.EXPIRED.value
    assert detail["statusChangedAt"] == "2026-11-14T11:30:00Z"
    assert mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers).json() == {
        "sales": []
    }
