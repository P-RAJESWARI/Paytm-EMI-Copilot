"""PaytmPaymentGatewayAdapter: offer discovery and Create Link over a fake Paytm transport."""

import json
from decimal import Decimal
from typing import Any

import httpx
import paytmchecksum
import pytest

from emi_copilot.adapters.payment_gateway.paytm_adapter import PaytmPaymentGatewayAdapter
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
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
    SYNTHETIC_MERCHANT_ID,
    SYNTHETIC_MERCHANT_KEY,
    TENURES_ROUTE,
    load_fixture,
    split_signed_body_text,
)
from tests.payment_builders import (
    CREATED_AT,
    build_offer_discovery_query,
    build_payment_link_request,
)


def reply_with(document: dict[str, Any], status_code: int = 200) -> httpx.Response:
    """Builds a scripted reply; Decimal amounts are written as text, which Paytm also uses."""
    return httpx.Response(status_code, content=json.dumps(document, default=str).encode("utf-8"))


def read_sent_body(request: httpx.Request) -> dict[str, Any]:
    """Parses the body object of a request the adapter sent."""
    _, body_text = split_signed_body_text(request)
    sent_body: dict[str, Any] = json.loads(body_text, parse_float=Decimal)
    return sent_body


@pytest.fixture
def under_test() -> PaytmAdapterUnderTest:
    """Gives a fresh Paytm adapter on a fresh fake server."""
    return build_paytm_adapter_under_test()


def test_paytm_adapter_is_the_paytm_payment_gateway_port(under_test: PaytmAdapterUnderTest) -> None:
    """The real adapter implements the port and calls itself "paytm"."""
    assert isinstance(under_test.adapter, PaymentGatewayPort)
    assert isinstance(under_test.adapter, PaytmPaymentGatewayAdapter)
    assert under_test.adapter.adapter_name == "paytm"


def test_discover_offers_asks_banks_then_tenures_with_signed_heads_and_mid_query(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """Banks, then Tenures for the one pair; each head is complete and its token is valid."""
    offers = under_test.adapter.discover_offers(build_offer_discovery_query())
    assert [offer.offer_id for offer in offers] == [
        "SYNTHETIC-PLAN-NO-COST-6M",
        "SYNTHETIC-PLAN-CASHBACK-12M",
        "SYNTHETIC-PLAN-STANDARD-6M",
    ]
    banks_request, tenures_request = under_test.server.received_requests
    assert banks_request.url.path.endswith("/emiSubvention/banks")
    assert tenures_request.url.path.endswith("/emiSubvention/tenures")
    for request_number, request in enumerate((banks_request, tenures_request), start=1):
        assert request.url.params["mid"] == SYNTHETIC_MERCHANT_ID
        assert request.headers["content-type"] == "application/json"
        head, body_text = split_signed_body_text(request)
        assert head["requestId"] == f"REQUEST{request_number:025d}"
        assert head["requestTimestamp"] == str(int(CREATED_AT.timestamp()))
        assert (head["version"], head["tokenType"]) == ("v1", "CHECKSUM")
        assert paytmchecksum.verifySignature(body_text, SYNTHETIC_MERCHANT_KEY, head["token"])
    assert read_sent_body(tenures_request)["filters"] == {
        "bankCode": "DEMOA",
        "cardType": "CREDIT_CARD",
    }


def test_discover_offers_asks_tenures_for_every_pair_and_shows_every_plan(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """Two bank and card pairs give two Tenures calls and all six plans, with no cap."""
    banks_document = load_fixture("banks_success.json")
    banks_document["body"]["emiTypes"][1]["cardTypes"].append({"cardType": "DEBIT_CARD"})
    debit_tenures_document = load_fixture("tenures_success.json")
    for plan in debit_tenures_document["body"]["planDetails"]:
        plan["planId"] += "-DEBIT"
    under_test.server.script(BANKS_ROUTE, reply_with(banks_document))
    under_test.server.script(
        TENURES_ROUTE,
        reply_with(load_fixture("tenures_success.json")),
        reply_with(debit_tenures_document),
    )
    offers = under_test.adapter.discover_offers(build_offer_discovery_query())
    assert len(offers) == 6
    tenures_requests = under_test.server.requests_to(TENURES_ROUTE)
    assert [read_sent_body(request)["filters"]["cardType"] for request in tenures_requests] == [
        "CREDIT_CARD",
        "DEBIT_CARD",
    ]


def test_discover_offers_with_two_plans_sharing_a_plan_id_raises(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """An offer id must pick one plan, so a repeated planId is a malformed answer [Verify]."""
    banks_document = load_fixture("banks_success.json")
    banks_document["body"]["emiTypes"][1]["cardTypes"].append({"cardType": "DEBIT_CARD"})
    under_test.server.script(BANKS_ROUTE, reply_with(banks_document))
    under_test.server.script(
        TENURES_ROUTE,
        reply_with(load_fixture("tenures_success.json")),
        reply_with(load_fixture("tenures_success.json")),
    )
    with pytest.raises(InvalidPaymentGatewayValueError):
        under_test.adapter.discover_offers(build_offer_discovery_query())


@pytest.mark.parametrize("refused_route", [BANKS_ROUTE, TENURES_ROUTE])
def test_discover_offers_refused_by_paytm_raises_request_rejected(
    under_test: PaytmAdapterUnderTest, refused_route: tuple[str, str]
) -> None:
    """A Banks or Tenures "F" answer is a refusal, never a silently shorter offer list."""
    under_test.server.script(refused_route, reply_with(load_fixture("tenures_failure.json")))
    with pytest.raises(PaymentGatewayRequestRejectedError) as raised:
        under_test.adapter.discover_offers(build_offer_discovery_query())
    assert raised.value.reason is PaymentGatewayRejectionReason.INVALID_REQUEST


def test_discover_offers_read_timeout_is_retried(under_test: PaytmAdapterUnderTest) -> None:
    """Banks is a read, so a read timeout is retried after a jittered sleep and then succeeds."""
    under_test.server.script(BANKS_ROUTE, httpx.ReadTimeout)
    assert len(under_test.adapter.discover_offers(build_offer_discovery_query())) == 3
    assert len(under_test.server.requests_to(BANKS_ROUTE)) == 2
    assert len(under_test.recorded_sleep_delays) == 1


def test_discover_offers_timing_out_on_every_attempt_raises_timeout(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """After the last allowed attempt a read timeout surfaces as PaymentGatewayTimeoutError."""
    under_test.server.script(BANKS_ROUTE, *[httpx.ReadTimeout] * 3)
    with pytest.raises(PaymentGatewayTimeoutError):
        under_test.adapter.discover_offers(build_offer_discovery_query())
    assert len(under_test.server.requests_to(BANKS_ROUTE)) == 3


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
