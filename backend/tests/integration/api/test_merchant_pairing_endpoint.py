"""POST /api/v1/merchants/pairing on the real application and the test database."""

from datetime import timedelta

import pytest

from emi_copilot.core.opaque_token import hash_opaque_token
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.merchant_api_helpers import (
    PAIRING_PATH,
    SYNTHETIC_PIN,
    WRONG_PIN,
    StoredShop,
    store_shop,
)
from tests.payment_builders import CREATED_AT

pytestmark = pytest.mark.integration

MERCHANT_ID = "01JCMERCHANTAPI00000000001"
SHOP_CODE = "RAVI-0193"


@pytest.fixture
def shop(mock_api: ApiHarness) -> StoredShop:
    """Stores the shop the pairing tests use."""
    return store_shop(mock_api, MERCHANT_ID, SHOP_CODE)


def test_pairing_with_right_pin_returns_201_token_profile_and_no_store(
    mock_api: ApiHarness, shop: StoredShop
) -> None:
    """The answer carries a bearer token, its expiry in UTC and the shop's profile."""
    response = mock_api.client.post(PAIRING_PATH, json={"shopId": SHOP_CODE, "pin": shop.pin})
    assert response.status_code == 201
    body = response.json()
    assert body == {
        "accessToken": body["accessToken"],
        "tokenType": "Bearer",
        "expiresAt": "2026-11-14T22:30:00Z",
        "merchant": {
            "merchantId": MERCHANT_ID,
            "shopId": SHOP_CODE,
            "shopName": f"Shop {SHOP_CODE}",
            "deviceLabel": "Counter tablet 1",
        },
    }
    assert response.headers["location"] == "/api/v1/merchants/me"
    assert response.headers["cache-control"] == "no-store"
    with SqlAlchemyUnitOfWork(mock_api.session_factory, mock_api.clock) as unit_of_work:
        stored_pairing = unit_of_work.device_pairings.find_by_access_token_hash(
            hash_opaque_token(body["accessToken"])
        )
    assert stored_pairing is not None
    assert stored_pairing.expires_at == CREATED_AT + timedelta(hours=12)


def test_pairing_with_lower_case_shop_id_pairs_the_same_shop(
    mock_api: ApiHarness, shop: StoredShop
) -> None:
    """Shop ids are matched in their printed upper-case form."""
    response = mock_api.client.post(PAIRING_PATH, json={"shopId": "ravi-0193", "pin": shop.pin})
    assert response.status_code == 201
    assert response.json()["merchant"]["shopId"] == SHOP_CODE


def test_pairing_unknown_shop_and_wrong_pin_get_identical_401_problems(
    mock_api: ApiHarness, shop: StoredShop
) -> None:
    """Apart from the correlation id the two answers are byte-for-byte the same."""
    unknown_shop_response = mock_api.client.post(
        PAIRING_PATH, json={"shopId": "SHOP-9999", "pin": shop.pin}
    )
    wrong_pin_response = mock_api.client.post(
        PAIRING_PATH, json={"shopId": SHOP_CODE, "pin": WRONG_PIN}
    )
    assert unknown_shop_response.status_code == wrong_pin_response.status_code == 401
    unknown_shop_problem = {**unknown_shop_response.json(), "correlationId": None}
    wrong_pin_problem = {**wrong_pin_response.json(), "correlationId": None}
    assert unknown_shop_problem == wrong_pin_problem
    assert wrong_pin_problem["code"] == "INVALID_PAIRING_CREDENTIALS"
    assert "www-authenticate" not in wrong_pin_response.headers


def test_pairing_sixth_attempt_after_five_wrong_pins_is_locked_even_with_right_pin(
    mock_api: ApiHarness, shop: StoredShop
) -> None:
    """Wrong PINs 1 to 5 answer 401; the 6th try answers 429 with Retry-After 900."""
    wrong_pin_statuses = [
        mock_api.client.post(PAIRING_PATH, json={"shopId": SHOP_CODE, "pin": WRONG_PIN}).status_code
        for _ in range(5)
    ]
    assert wrong_pin_statuses == [401] * 5
    locked_response = mock_api.client.post(
        PAIRING_PATH, json={"shopId": SHOP_CODE, "pin": shop.pin}
    )
    assert locked_response.status_code == 429
    assert locked_response.headers["retry-after"] == "900"
    assert locked_response.json()["code"] == "PAIRING_TEMPORARILY_LOCKED"


def test_pairing_after_the_fifteen_minute_lock_accepts_the_right_pin(
    mock_api: ApiHarness, shop: StoredShop
) -> None:
    """The lock is stored in the database and ends by itself after 15 minutes."""
    for _ in range(5):
        mock_api.client.post(PAIRING_PATH, json={"shopId": SHOP_CODE, "pin": WRONG_PIN})
    mock_api.clock.advance(timedelta(minutes=15))
    response = mock_api.client.post(PAIRING_PATH, json={"shopId": SHOP_CODE, "pin": shop.pin})
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("body", "invalid_field"),
    [
        ({"shopId": SHOP_CODE, "pin": "13579"}, "pin"),
        ({"shopId": SHOP_CODE, "pin": "1357900"}, "pin"),
        ({"shopId": SHOP_CODE, "pin": "13579a"}, "pin"),
        ({"shopId": SHOP_CODE, "pin": 135790}, "pin"),
        ({"shopId": "RAVI 0193", "pin": SYNTHETIC_PIN}, "shopId"),
        ({"shopId": "", "pin": SYNTHETIC_PIN}, "shopId"),
        ({"pin": SYNTHETIC_PIN}, "shopId"),
        ({"shopId": SHOP_CODE, "pin": SYNTHETIC_PIN, "deviceLabel": "x"}, "deviceLabel"),
    ],
)
@pytest.mark.usefixtures("shop")
def test_pairing_with_invalid_body_returns_422_naming_the_field_without_echoing_it(
    mock_api: ApiHarness, body: dict[str, object], invalid_field: str
) -> None:
    """A malformed PIN or shop id is refused before any lookup, and the value is not echoed."""
    response = mock_api.client.post(PAIRING_PATH, json=body)
    assert response.status_code == 422
    problem = response.json()
    assert problem["code"] == "REQUEST_VALIDATION_FAILED"
    assert [field_error["field"] for field_error in problem["fieldErrors"]] == [invalid_field]
    assert str(body.get("pin", "no-pin-sent")) not in response.text


def test_pairing_with_malformed_json_returns_400(mock_api: ApiHarness) -> None:
    """A body that is not JSON is a malformed request."""
    response = mock_api.client.post(
        PAIRING_PATH, content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "MALFORMED_REQUEST"


def test_pairing_more_than_ten_requests_a_minute_from_one_client_is_rate_limited(
    mock_api: ApiHarness, shop: StoredShop
) -> None:
    """The 11th request in a window answers 429 RATE_LIMITED; the next window is open again."""
    statuses = [
        mock_api.client.post(PAIRING_PATH, json={"shopId": "SHOP-9999", "pin": WRONG_PIN})
        for _ in range(11)
    ]
    assert [response.status_code for response in statuses] == [401] * 10 + [429]
    assert statuses[-1].json()["code"] == "RATE_LIMITED"
    assert statuses[-1].headers["retry-after"] == "60"
    mock_api.clock.advance(timedelta(seconds=60))
    response = mock_api.client.post(PAIRING_PATH, json={"shopId": SHOP_CODE, "pin": shop.pin})
    assert response.status_code == 201
