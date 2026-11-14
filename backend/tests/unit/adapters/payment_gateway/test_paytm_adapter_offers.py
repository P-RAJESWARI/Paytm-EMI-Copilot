"""PaytmPaymentGatewayAdapter: offer discovery over a fake Paytm transport."""

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
from tests.contract.payment_gateway.paytm_adapter_builder import (
    PaytmAdapterUnderTest,
    build_paytm_adapter_under_test,
)
from tests.contract.payment_gateway.paytm_fake_server import (
    BANKS_ROUTE,
    SYNTHETIC_MERCHANT_ID,
    SYNTHETIC_MERCHANT_KEY,
    TENURES_ROUTE,
    load_fixture,
    read_sent_body,
    reply_with,
    split_signed_body_text,
)
from tests.payment_builders import CREATED_AT, build_offer_discovery_query


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


@pytest.mark.parametrize(
    ("second_tenures_answers", "expected_error_type"),
    [
        ([reply_with(load_fixture("tenures_failure.json"))], PaymentGatewayRequestRejectedError),
        ([httpx.Response(400)], PaymentGatewayRequestRejectedError),
        ([httpx.Response(503)] * 3, PaymentGatewayUnavailableError),
        ([httpx.ReadTimeout] * 3, PaymentGatewayTimeoutError),
    ],
    ids=["refused-f", "http-400", "server-errors", "read-timeouts"],
)
def test_discover_offers_with_one_failed_tenures_call_fails_whole_call_adr_0011(
    under_test: PaytmAdapterUnderTest,
    second_tenures_answers: list[httpx.Response | type[httpx.RequestError]],
    expected_error_type: type[Exception],
) -> None:
    """ADR 0011 decision 3: one failed Tenures call of two raises; no partial offer list."""
    banks_document = load_fixture("banks_success.json")
    banks_document["body"]["emiTypes"][1]["cardTypes"].append({"cardType": "DEBIT_CARD"})
    under_test.server.script(BANKS_ROUTE, reply_with(banks_document))
    under_test.server.script(
        TENURES_ROUTE, reply_with(load_fixture("tenures_success.json")), *second_tenures_answers
    )
    with pytest.raises(expected_error_type):
        under_test.adapter.discover_offers(build_offer_discovery_query())
    tenures_requests = under_test.server.requests_to(TENURES_ROUTE)
    assert len(tenures_requests) == 1 + len(second_tenures_answers)


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
