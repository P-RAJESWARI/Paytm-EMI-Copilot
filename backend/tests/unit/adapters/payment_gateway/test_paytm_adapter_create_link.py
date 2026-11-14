"""PaytmPaymentGatewayAdapter: Create Link over a fake Paytm transport, sent at most once."""

import httpx
import paytmchecksum
import pytest

from emi_copilot.domain.errors import (
    InvalidPaymentGatewayValueError,
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
    PaymentGatewayTimeoutError,
    PaymentGatewayUnavailableError,
)
from emi_copilot.domain.payments import PaymentLink
from tests.contract.payment_gateway.paytm_adapter_builder import (
    SYNTHETIC_WEBHOOK_CALLBACK_URL,
    PaytmAdapterUnderTest,
    build_paytm_adapter_under_test,
)
from tests.contract.payment_gateway.paytm_fake_server import (
    BANKS_ROUTE,
    CREATE_LINK_ROUTE,
    SYNTHETIC_MERCHANT_KEY,
    load_fixture,
    read_sent_body,
    reply_with,
    split_signed_body_text,
)
from tests.payment_builders import build_offer_discovery_query, build_payment_link_request


@pytest.fixture
def under_test() -> PaytmAdapterUnderTest:
    """Gives a fresh Paytm adapter on a fresh fake server."""
    return build_paytm_adapter_under_test()


def test_create_payment_link_sends_signed_fixed_link_and_returns_short_url(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """One request whose AES head signs the exact body bytes; the short URL comes back."""
    request = build_payment_link_request()
    payment_link = under_test.adapter.create_payment_link(request)
    assert payment_link == PaymentLink(
        order_id=request.order_id,
        gateway_link_id="90000001",
        payment_url="https://short-link.example.test/SYNTHLINK0001",
    )
    (sent_request,) = under_test.server.received_requests
    assert sent_request.url.path == "/link/create"
    assert sent_request.url.query == b""
    head, body_text = split_signed_body_text(sent_request)
    assert head["tokenType"] == "AES"
    assert paytmchecksum.verifySignature(body_text, SYNTHETIC_MERCHANT_KEY, head["signature"])
    assert '"amount":22000.00,' in body_text
    sent_body = read_sent_body(sent_request)
    assert sent_body["statusCallbackUrl"] == SYNTHETIC_WEBHOOK_CALLBACK_URL
    assert "partialPayment" not in sent_body
    assert "bindLinkIdMobile" not in sent_body


def test_create_payment_link_uses_send_non_idempotent_only(
    under_test: PaytmAdapterUnderTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Create Link never goes through the retrying path (ADR 0005)."""

    def refuse_retrying_send(_request: httpx.Request) -> httpx.Response:
        """Fails the test if the retrying path is used."""
        raise AssertionError("create_payment_link must not use send_idempotent")

    monkeypatch.setattr(under_test.resilient_client, "send_idempotent", refuse_retrying_send)
    under_test.adapter.create_payment_link(build_payment_link_request())


@pytest.mark.parametrize(
    ("scripted_answer", "expected_error_type"),
    [
        (httpx.ReadTimeout, PaymentGatewayTimeoutError),
        (httpx.WriteTimeout, PaymentGatewayTimeoutError),
        (httpx.RemoteProtocolError, PaymentGatewayTimeoutError),
        (httpx.Response(503), PaymentGatewayTimeoutError),
        (httpx.Response(500), PaymentGatewayTimeoutError),
        (httpx.ConnectError, PaymentGatewayUnavailableError),
        (httpx.ConnectTimeout, PaymentGatewayUnavailableError),
    ],
    ids=[
        "read-timeout",
        "write-timeout",
        "dropped-after-sending",
        "503",
        "500",
        "connect-error",
        "connect-timeout",
    ],
)
def test_create_payment_link_failure_is_sent_once_and_follows_adr_0010(
    under_test: PaytmAdapterUnderTest,
    scripted_answer: httpx.Response | type[httpx.RequestError],
    expected_error_type: type[Exception],
) -> None:
    """Possibly-sent failures (timeouts, 5xx) are Timeout; never-sent are Unavailable; no retry."""
    under_test.server.script(CREATE_LINK_ROUTE, scripted_answer)
    with pytest.raises(expected_error_type):
        under_test.adapter.create_payment_link(build_payment_link_request())
    assert len(under_test.server.requests_to(CREATE_LINK_ROUTE)) == 1
    assert under_test.recorded_sleep_delays == []


def test_create_payment_link_with_open_circuit_sends_nothing_and_is_unavailable() -> None:
    """Once the breaker is open nothing is sent, so the outcome is known: Unavailable."""
    under_test = build_paytm_adapter_under_test(max_attempts=1, failure_threshold=1)
    under_test.server.script(BANKS_ROUTE, httpx.Response(503))
    with pytest.raises(PaymentGatewayUnavailableError):
        under_test.adapter.discover_offers(build_offer_discovery_query())
    with pytest.raises(PaymentGatewayUnavailableError):
        under_test.adapter.create_payment_link(build_payment_link_request())
    assert under_test.server.requests_to(CREATE_LINK_ROUTE) == []


def test_create_payment_link_refused_with_documented_code_raises_request_rejected(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """Result code 5028 (invalid checksum) is a refusal with our INVALID_REQUEST reason."""
    under_test.server.script(
        CREATE_LINK_ROUTE, reply_with(load_fixture("create_link_failure.json"))
    )
    with pytest.raises(PaymentGatewayRequestRejectedError) as raised:
        under_test.adapter.create_payment_link(build_payment_link_request())
    assert raised.value.reason is PaymentGatewayRejectionReason.INVALID_REQUEST


@pytest.mark.parametrize("result_code", ["501", "502"], ids=["internal-501", "unknown-502"])
def test_create_payment_link_body_code_501_or_502_is_a_refusal_sent_once_adr_0011(
    under_test: PaytmAdapterUnderTest, result_code: str
) -> None:
    """ADR 0011 decision 2: a readable FAILED body with 501 or 502 is rejected, not unknown."""
    failure_document = load_fixture("create_link_failure.json")
    failure_document["body"]["resultInfo"]["resultCode"] = result_code
    under_test.server.script(CREATE_LINK_ROUTE, reply_with(failure_document))
    with pytest.raises(PaymentGatewayRequestRejectedError) as raised:
        under_test.adapter.create_payment_link(build_payment_link_request())
    assert raised.value.reason is PaymentGatewayRejectionReason.GATEWAY_INTERNAL_ERROR
    assert len(under_test.server.requests_to(CREATE_LINK_ROUTE)) == 1


@pytest.mark.parametrize(
    ("scripted_reply", "expected_error_type"),
    [
        (httpx.Response(400, content=b"refused"), PaymentGatewayRequestRejectedError),
        (httpx.Response(200, content=b"<html>not json</html>"), InvalidPaymentGatewayValueError),
        (httpx.Response(200, content=b'{"head": {}}'), InvalidPaymentGatewayValueError),
    ],
    ids=["http-400", "not-json", "no-body"],
)
def test_create_payment_link_with_unusable_reply_raises_typed_error(
    under_test: PaytmAdapterUnderTest,
    scripted_reply: httpx.Response,
    expected_error_type: type[Exception],
) -> None:
    """An HTTP refusal or an unreadable reply becomes a typed domain error, never raw text."""
    under_test.server.script(CREATE_LINK_ROUTE, scripted_reply)
    with pytest.raises(expected_error_type):
        under_test.adapter.create_payment_link(build_payment_link_request())


def test_create_payment_link_with_too_long_order_id_sends_nothing(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """An order id Paytm cannot hold is refused before any byte is sent."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        under_test.adapter.create_payment_link(build_payment_link_request(order_id="O" * 51))
    assert under_test.server.received_requests == []


def test_create_payment_link_without_callback_url_sends_none() -> None:
    """With no webhook URL configured, the link carries no statusCallbackUrl."""
    under_test = build_paytm_adapter_under_test(webhook_callback_url=None)
    under_test.adapter.create_payment_link(build_payment_link_request())
    (sent_request,) = under_test.server.received_requests
    assert "statusCallbackUrl" not in read_sent_body(sent_request)
