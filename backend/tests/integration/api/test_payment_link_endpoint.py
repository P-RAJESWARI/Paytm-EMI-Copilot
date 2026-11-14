"""POST /api/v1/payment-links: idempotency, Location, audit and unknown outcomes (ADR 0005)."""

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import MOCK_PAYMENT_URL_PREFIX
from emi_copilot.domain.errors import PaymentGatewayTimeoutError
from emi_copilot.domain.payments import AuditEventType, PaymentAttemptStatus
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.integration.api.api_harness import SAMPLE_ITEM_QUERY, ApiHarness
from tests.integration.api.merchant_api_helpers import sign_in_as_a_shop

pytestmark = pytest.mark.integration

IDEMPOTENCY_KEY = "idempotency-key-api-0001"
MOCK_PLAN_B_REQUEST = {**SAMPLE_ITEM_QUERY, "offerId": "mock-offer-card-6m"}
FAKE_PLAN_B_REQUEST = {**SAMPLE_ITEM_QUERY, "offerId": "offer-plan-b"}


@pytest.fixture
def fake_api(fake_api: ApiHarness) -> ApiHarness:
    """The fake-gateway application, signed in as a paired shop (plan Q16)."""
    sign_in_as_a_shop(fake_api)
    return fake_api


@pytest.fixture
def mock_api(mock_api: ApiHarness) -> ApiHarness:
    """The Mock-gateway application, signed in as a paired shop (plan Q16)."""
    sign_in_as_a_shop(mock_api)
    return mock_api


def test_post_payment_link_returns_201_with_location_snapshot_and_audit_row(
    mock_api: ApiHarness,
) -> None:
    """A new key makes the link, points Location at its status and audits the creation."""
    response = mock_api.client.post(
        "/api/v1/payment-links",
        json=MOCK_PLAN_B_REQUEST,
        headers={"Idempotency-Key": IDEMPOTENCY_KEY},
    )
    assert response.status_code == 201
    body = response.json()
    order_id = body["orderId"]
    assert response.headers["Location"] == f"/api/v1/payments/{order_id}/status"
    assert body["paymentUrl"].startswith(MOCK_PAYMENT_URL_PREFIX)
    assert body["status"] == "AWAITING_PAYMENT"
    assert body["offer"] == {
        "offerId": "mock-offer-card-6m",
        "lenderLabel": "Your card's bank",
        "emiType": "STANDARD",
        "tenureInMonths": 6,
        "regularInstallmentInPaise": 385_000,
        "lastInstallmentInPaise": 385_000,
        "extraInTotalInPaise": 110_000,
        "totalPayableInPaise": 2_310_000,
        "priceInPaise": 2_200_000,
    }
    stored_attempt = mock_api.read_attempt(order_id)
    assert stored_attempt is not None
    assert stored_attempt.status is PaymentAttemptStatus.LINK_CREATED
    created_events = mock_api.read_audit_events(AuditEventType.PAYMENT_LINK_CREATED)
    assert [event.subject_id for event in created_events] == [stored_attempt.id]
    assert created_events[0].correlation_id == response.headers["X-Correlation-Id"]


def test_post_payment_link_without_idempotency_key_returns_422_problem(
    fake_api: ApiHarness, fake_gateway: FakePaymentGateway
) -> None:
    """The key is required; its absence is a field error and nothing reaches the gateway."""
    response = fake_api.client.post("/api/v1/payment-links", json=FAKE_PLAN_B_REQUEST)
    assert response.status_code == 422
    problem = response.json()
    assert problem["code"] == "REQUEST_VALIDATION_FAILED"
    assert problem["fieldErrors"] == [{"field": "Idempotency-Key", "message": "Field required"}]
    assert fake_gateway.create_link_calls == []


@pytest.mark.parametrize("invalid_key", ["short", "has a space in it", "x" * 256, "naïve-key-01"])
def test_post_payment_link_with_malformed_idempotency_key_returns_422_problem(
    fake_api: ApiHarness, invalid_key: str
) -> None:
    """Keys shorter than 8, longer than 255 or outside visible ASCII are refused."""
    response = fake_api.client.post(
        "/api/v1/payment-links",
        json=FAKE_PLAN_B_REQUEST,
        headers={"Idempotency-Key": invalid_key.encode("utf-8")},
    )
    assert response.status_code == 422
    assert response.json()["fieldErrors"][0]["field"] == "Idempotency-Key"


def test_post_payment_link_replay_with_same_body_returns_identical_response_and_one_call(
    fake_api: ApiHarness, fake_gateway: FakePaymentGateway
) -> None:
    """The same key and body give the original 201 response; the gateway was called once."""
    headers = {"Idempotency-Key": IDEMPOTENCY_KEY}
    first_response = fake_api.client.post(
        "/api/v1/payment-links", json=FAKE_PLAN_B_REQUEST, headers=headers
    )
    replay_response = fake_api.client.post(
        "/api/v1/payment-links", json=FAKE_PLAN_B_REQUEST, headers=headers
    )
    assert first_response.status_code == replay_response.status_code == 201
    assert replay_response.json() == first_response.json()
    assert replay_response.headers["Location"] == first_response.headers["Location"]
    assert len(fake_gateway.create_link_calls) == 1


def test_post_payment_link_replay_with_different_body_returns_422_key_reused(
    fake_api: ApiHarness, fake_gateway: FakePaymentGateway
) -> None:
    """Reusing a key for another body is refused and nothing is re-sent."""
    headers = {"Idempotency-Key": IDEMPOTENCY_KEY}
    fake_api.client.post("/api/v1/payment-links", json=FAKE_PLAN_B_REQUEST, headers=headers)
    response = fake_api.client.post(
        "/api/v1/payment-links",
        json={**FAKE_PLAN_B_REQUEST, "offerId": "offer-plan-a"},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert len(fake_gateway.create_link_calls) == 1


def test_post_payment_link_on_gateway_timeout_returns_504_then_409_on_replay(
    fake_api: ApiHarness, fake_gateway: FakePaymentGateway
) -> None:
    """A timed-out create is never retried; the key then answers outcome unknown."""
    fake_gateway.create_link_error = PaymentGatewayTimeoutError("The gateway did not answer.")
    headers = {"Idempotency-Key": IDEMPOTENCY_KEY}
    timeout_response = fake_api.client.post(
        "/api/v1/payment-links", json=FAKE_PLAN_B_REQUEST, headers=headers
    )
    assert timeout_response.status_code == 504
    assert timeout_response.json()["code"] == "PAYMENT_GATEWAY_TIMEOUT"
    assert len(fake_gateway.create_link_calls) == 1
    replay_response = fake_api.client.post(
        "/api/v1/payment-links", json=FAKE_PLAN_B_REQUEST, headers=headers
    )
    assert replay_response.status_code == 409
    assert replay_response.json()["code"] == "PAYMENT_LINK_OUTCOME_UNKNOWN"
    assert len(fake_gateway.create_link_calls) == 1


def test_post_payment_link_for_unquoted_offer_returns_404_offer_not_found(
    fake_api: ApiHarness,
) -> None:
    """An offer id the gateway does not quote for the item is not found."""
    response = fake_api.client.post(
        "/api/v1/payment-links",
        json={**FAKE_PLAN_B_REQUEST, "offerId": "offer-that-does-not-exist"},
        headers={"Idempotency-Key": IDEMPOTENCY_KEY},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "OFFER_NOT_FOUND"


@pytest.mark.parametrize(
    "body_override",
    [{"priceInPaise": "2200000"}, {"priceInPaise": 2200000.0}, {"cardNumber": "4111"}],
)
def test_post_payment_link_with_non_integer_money_or_unknown_field_returns_422(
    fake_api: ApiHarness, body_override: dict[str, object]
) -> None:
    """Money must be a JSON integer, and unknown fields such as card data are refused."""
    response = fake_api.client.post(
        "/api/v1/payment-links",
        json={**FAKE_PLAN_B_REQUEST, **body_override},
        headers={"Idempotency-Key": IDEMPOTENCY_KEY},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_FAILED"


def test_post_payment_link_with_invalid_json_returns_400_malformed_request(
    fake_api: ApiHarness,
) -> None:
    """A body that is not JSON is malformed (api-conventions.md section 3)."""
    response = fake_api.client.post(
        "/api/v1/payment-links",
        content=b"{not json",
        headers={"Idempotency-Key": IDEMPOTENCY_KEY, "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "MALFORMED_REQUEST"


def test_post_payment_link_without_a_merchant_token_returns_401_and_calls_nothing(
    fake_api: ApiHarness, fake_gateway: FakePaymentGateway
) -> None:
    """Since Layer 2 only a signed-in shop may hand a plan to the gateway (plan Q16)."""
    fake_api.client.headers.pop("Authorization")
    response = fake_api.client.post(
        "/api/v1/payment-links",
        json=FAKE_PLAN_B_REQUEST,
        headers={"Idempotency-Key": IDEMPOTENCY_KEY},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "MERCHANT_AUTHENTICATION_REQUIRED"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert fake_gateway.discover_offers_calls == []
