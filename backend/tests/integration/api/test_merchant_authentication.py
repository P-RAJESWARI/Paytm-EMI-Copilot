"""Bearer authentication of merchant endpoints, through GET /api/v1/merchants/me."""

from datetime import timedelta

import pytest

from emi_copilot.core.opaque_token import hash_opaque_token
from emi_copilot.domain.merchants import DevicePairing
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.merchant_api_helpers import (
    StoredShop,
    pair_and_get_bearer_headers,
    store_shop,
)
from tests.payment_builders import CREATED_AT

pytestmark = pytest.mark.integration

MERCHANT_ID = "01JCMERCHANTAUTH0000000001"
ME_PATH = "/api/v1/merchants/me"
SYNTHETIC_REVOKED_BEARER_VALUE = "synthetic-revoked-bearer-value"


@pytest.fixture
def shop(mock_api: ApiHarness) -> StoredShop:
    """Stores the shop whose devices the tests pair."""
    return store_shop(mock_api, MERCHANT_ID, "SHOP-AUTH")


def assert_authentication_required(response_status: int, problem: dict[str, object]) -> None:
    """Checks a refusal is the one 401 problem every bad token gets."""
    assert response_status == 401
    assert problem["code"] == "MERCHANT_AUTHENTICATION_REQUIRED"


def test_me_with_paired_token_returns_the_shop_and_device(
    mock_api: ApiHarness, shop: StoredShop
) -> None:
    """The profile names the signed-in shop and device, and nothing about customers."""
    response = mock_api.client.get(ME_PATH, headers=pair_and_get_bearer_headers(mock_api, shop))
    assert response.status_code == 200
    assert response.json() == {
        "merchantId": MERCHANT_ID,
        "shopId": "SHOP-AUTH",
        "shopName": "Shop SHOP-AUTH",
        "deviceLabel": "Counter tablet 1",
    }


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer"},
        {"Authorization": "Basic c3ludGhldGljOnZhbHVl"},
        {"Authorization": "Bearer synthetic-never-issued-bearer-value"},
    ],
    ids=["no-header", "empty-bearer", "basic-scheme", "unknown-token"],
)
def test_me_without_a_usable_bearer_token_returns_401_with_bearer_challenge(
    mock_api: ApiHarness, headers: dict[str, str]
) -> None:
    """Every kind of missing or wrong credential gets the same problem and challenge."""
    response = mock_api.client.get(ME_PATH, headers=headers)
    assert_authentication_required(response.status_code, response.json())
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["content-type"] == "application/problem+json"


def test_me_with_expired_token_returns_401(mock_api: ApiHarness, shop: StoredShop) -> None:
    """After 12 hours the token stops working."""
    bearer_headers = pair_and_get_bearer_headers(mock_api, shop)
    mock_api.clock.advance(timedelta(hours=12))
    response = mock_api.client.get(ME_PATH, headers=bearer_headers)
    assert_authentication_required(response.status_code, response.json())


def test_me_with_revoked_token_returns_401(mock_api: ApiHarness, shop: StoredShop) -> None:
    """A revoked pairing is refused before its expiry."""
    with SqlAlchemyUnitOfWork(mock_api.session_factory, mock_api.clock) as unit_of_work:
        unit_of_work.device_pairings.add(
            DevicePairing(
                id="01JCPAIRINGREVOKED00000001",
                merchant_id=shop.merchant_id,
                device_label="Counter tablet 2",
                access_token_hash=hash_opaque_token(SYNTHETIC_REVOKED_BEARER_VALUE),
                expires_at=CREATED_AT + timedelta(hours=12),
                revoked_at=CREATED_AT,
            )
        )
    response = mock_api.client.get(
        ME_PATH, headers={"Authorization": f"Bearer {SYNTHETIC_REVOKED_BEARER_VALUE}"}
    )
    assert_authentication_required(response.status_code, response.json())
