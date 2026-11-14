"""POST /api/v1/webhooks/paytm: signature first, idempotent application, bounded body."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.mock_webhook_signature import MOCK_SIGNATURE_FIELD
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType, GatewayPaymentStatus, PaymentAttemptStatus
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import SAMPLE_ITEM_QUERY, ApiHarness, open_api_harness
from tests.integration.api.merchant_api_helpers import sign_in_as_a_shop

pytestmark = pytest.mark.integration

WEBHOOK_PATH = "/api/v1/webhooks/paytm"


@pytest.fixture
def mock_api(mock_api: ApiHarness) -> ApiHarness:
    """The Mock-gateway application, signed in as a paired shop to create the links."""
    sign_in_as_a_shop(mock_api)
    return mock_api


def _create_payment_link(mock_api: ApiHarness) -> str:
    """Creates a link for design plan B and returns its order id."""
    response = mock_api.client.post(
        "/api/v1/payment-links",
        json={**SAMPLE_ITEM_QUERY, "offerId": "mock-offer-card-6m"},
        headers={"Idempotency-Key": "idempotency-key-webhook-0001"},
    )
    assert response.status_code == 201
    order_id: str = response.json()["orderId"]
    return order_id


def _build_paid_webhook_fields(
    mock_gateway: MockPaymentGatewayAdapter, order_id: str
) -> dict[str, str]:
    """Builds the form fields of a correctly signed PAID notification for the order."""
    notification = mock_gateway.build_signed_notification(
        order_id, GatewayPaymentStatus.PAID, "mock-transaction-0001", Money.from_paise(2_200_000)
    )
    return dict(notification.received_fields)


def test_post_webhook_with_bad_signature_returns_401_and_audits_rejection(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter
) -> None:
    """A tampered notification is refused, audited as WEBHOOK_REJECTED, and changes nothing."""
    order_id = _create_payment_link(mock_api)
    tampered_fields = {
        **_build_paid_webhook_fields(mock_gateway, order_id),
        MOCK_SIGNATURE_FIELD: "0" * 64,
    }
    response = mock_api.client.post(WEBHOOK_PATH, data=tampered_fields)
    assert response.status_code == 401
    assert response.json()["code"] == "WEBHOOK_SIGNATURE_INVALID"
    rejected_events = mock_api.read_audit_events(AuditEventType.WEBHOOK_REJECTED)
    assert len(rejected_events) == 1
    assert rejected_events[0].details["rejection_code"] == "WEBHOOK_SIGNATURE_INVALID"
    stored_attempt = mock_api.read_attempt(order_id)
    assert stored_attempt is not None
    assert stored_attempt.status is PaymentAttemptStatus.LINK_CREATED


def test_post_valid_webhook_returns_202_without_body_and_marks_paid(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter
) -> None:
    """A verified PAID notification answers 202 and moves the attempt to PAID."""
    order_id = _create_payment_link(mock_api)
    response = mock_api.client.post(
        WEBHOOK_PATH, data=_build_paid_webhook_fields(mock_gateway, order_id)
    )
    assert response.status_code == 202
    assert response.content == b""
    stored_attempt = mock_api.read_attempt(order_id)
    assert stored_attempt is not None
    assert stored_attempt.status is PaymentAttemptStatus.PAID


def test_post_repeated_valid_webhook_returns_202_and_writes_nothing_more(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter
) -> None:
    """The gateway's repeat of a notification has no extra effect."""
    order_id = _create_payment_link(mock_api)
    webhook_fields = _build_paid_webhook_fields(mock_gateway, order_id)
    mock_api.client.post(WEBHOOK_PATH, data=webhook_fields)
    audit_event_count_after_first = mock_api.count_all_audit_events()
    repeat_response = mock_api.client.post(WEBHOOK_PATH, data=webhook_fields)
    assert repeat_response.status_code == 202
    assert mock_api.count_all_audit_events() == audit_event_count_after_first
    assert len(mock_api.read_audit_events(AuditEventType.PAYMENT_STATUS_CHANGED)) == 1


def test_post_valid_webhook_for_unknown_order_returns_202(
    mock_api: ApiHarness, mock_gateway: MockPaymentGatewayAdapter
) -> None:
    """A verified notification about an order that is not ours is accepted and audited only."""
    response = mock_api.client.post(
        WEBHOOK_PATH, data=_build_paid_webhook_fields(mock_gateway, "01JD0000000000000000UNKNWN")
    )
    assert response.status_code == 202
    assert len(mock_api.read_audit_events(AuditEventType.WEBHOOK_PROCESSED)) == 1


def test_post_oversized_webhook_returns_413_without_reaching_the_service(
    mock_api: ApiHarness,
) -> None:
    """A body above 16 KiB is refused before it is parsed or verified."""
    response = mock_api.client.post(
        WEBHOOK_PATH,
        content=b"padding=" + b"x" * (16 * 1024),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "REQUEST_BODY_TOO_LARGE"
    assert mock_api.read_audit_events(AuditEventType.WEBHOOK_REJECTED) == []


def test_post_streamed_oversized_webhook_without_length_returns_413(mock_api: ApiHarness) -> None:
    """A chunked body with no Content-Length is cut off once it passes the limit."""

    def generate_body_chunks() -> Iterator[bytes]:
        """Yields 20 KiB of form data in 1 KiB chunks."""
        for _ in range(20):
            yield b"x" * 1024

    response = mock_api.client.post(
        WEBHOOK_PATH,
        content=generate_body_chunks(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 413


def test_post_webhook_as_json_returns_415(mock_api: ApiHarness) -> None:
    """Only form-encoded notifications are accepted (ADR 0002 [Verify])."""
    response = mock_api.client.post(WEBHOOK_PATH, json={"orderId": "x"})
    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.parametrize("malformed_body", [b"orderId=a&orderId=b", b"no-equals-sign", b"\xff=1"])
def test_post_webhook_with_unparseable_form_returns_400(
    mock_api: ApiHarness, malformed_body: bytes
) -> None:
    """Repeated names, broken pairs and non-UTF-8 bytes are malformed, never guessed at."""
    response = mock_api.client.post(
        WEBHOOK_PATH,
        content=malformed_body,
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "MALFORMED_REQUEST"


def test_post_empty_webhook_returns_401_and_audits_rejection(mock_api: ApiHarness) -> None:
    """An empty form carries no signature, so it is refused by verification and audited."""
    response = mock_api.client.post(
        WEBHOOK_PATH, content=b"", headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401
    assert len(mock_api.read_audit_events(AuditEventType.WEBHOOK_REJECTED)) == 1


@pytest.fixture
def webhook_limited_api(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
) -> Iterator[ApiHarness]:
    """Runs the application with two webhooks a minute per client address."""
    settings = ApplicationSettings(payment_webhook_rate_limit_max_requests=2)
    with open_api_harness(session_factory, fixed_clock, mock_gateway, settings) as harness:
        yield harness


def test_post_webhooks_over_the_client_limit_return_429_before_the_body_is_read(
    webhook_limited_api: ApiHarness,
) -> None:
    """A flood is refused before any signature work; nothing is audited for the refused ones."""
    unsigned_fields = {"orderId": "ORDER-UNSIGNED-0001"}
    responses = [
        webhook_limited_api.client.post(WEBHOOK_PATH, data=unsigned_fields) for _ in range(3)
    ]
    assert [response.status_code for response in responses] == [401, 401, 429]
    assert responses[2].json()["code"] == "RATE_LIMITED"
    assert int(responses[2].headers["Retry-After"]) >= 1
    assert len(webhook_limited_api.read_audit_events(AuditEventType.WEBHOOK_REJECTED)) == 2
