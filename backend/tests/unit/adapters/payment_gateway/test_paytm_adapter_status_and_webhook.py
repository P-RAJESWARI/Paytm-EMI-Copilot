"""PaytmPaymentGatewayAdapter: v3 status with reply signatures, webhooks, and what is logged."""

import json
import logging
from typing import Any

import httpx
import paytmchecksum
import pytest

from emi_copilot.adapters.payment_gateway import paytm_adapter
from emi_copilot.core.logging import configure_logging
from emi_copilot.domain.errors import (
    InvalidPaymentGatewayValueError,
    PaymentGatewayError,
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
    PaymentGatewayTimeoutError,
    PaymentGatewayUnavailableError,
    WebhookSignatureInvalidError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    GatewayPaymentStatus,
    PaymentStatusResult,
    UnverifiedWebhookNotification,
)
from tests.contract.payment_gateway.paytm_adapter_builder import (
    PaytmAdapterUnderTest,
    build_paytm_adapter_under_test,
)
from tests.contract.payment_gateway.paytm_fake_server import (
    BANKS_ROUTE,
    STATUS_ROUTE,
    SYNTHETIC_MERCHANT_ID,
    SYNTHETIC_MERCHANT_KEY,
    TENURES_ROUTE,
    load_fixture,
    sign_status_reply,
    split_signed_body_text,
)
from tests.payment_builders import build_offer_discovery_query, build_payment_link_request

ORDER_ID = "ORDER-SAMPLE-0001"


@pytest.fixture
def under_test() -> PaytmAdapterUnderTest:
    """Gives a fresh Paytm adapter on a fresh fake server."""
    return build_paytm_adapter_under_test()


def build_signed_notification(**changed_fields: str) -> UnverifiedWebhookNotification:
    """Builds a genuinely signed success webhook, with single fields changed BEFORE signing."""
    webhook_fields: dict[str, str] = load_fixture("webhook_form_fields.json")
    webhook_fields.update(changed_fields)
    checksum = paytmchecksum.generateSignature(dict(webhook_fields), SYNTHETIC_MERCHANT_KEY)
    return UnverifiedWebhookNotification(
        received_fields={**webhook_fields, "CHECKSUMHASH": checksum}
    )


def test_get_payment_status_sends_signed_mid_and_order_id_and_reads_the_signed_reply(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """The v3 body is mid and orderId only, signed in the head; the signed reply is trusted."""
    under_test.adapter.create_payment_link(build_payment_link_request())
    under_test.server.mark_order_paid(ORDER_ID)
    assert under_test.adapter.get_payment_status(ORDER_ID) == PaymentStatusResult(
        ORDER_ID, GatewayPaymentStatus.PAID, "SYNTHETIC-TXN-0001", Money.from_rupees("22000")
    )
    status_request = under_test.server.requests_to(STATUS_ROUTE)[0]
    assert status_request.url.host == "securegw-stage.paytmpayments.in"
    assert status_request.url.query == b""
    head, body_text = split_signed_body_text(status_request)
    assert json.loads(body_text) == {"mid": SYNTHETIC_MERCHANT_ID, "orderId": ORDER_ID}
    assert set(head) == {"signature"}
    assert paytmchecksum.verifySignature(body_text, SYNTHETIC_MERCHANT_KEY, head["signature"])


def test_get_payment_status_read_timeout_is_retried(under_test: PaytmAdapterUnderTest) -> None:
    """Status is idempotent, so a read timeout is retried and the next answer is used."""
    under_test.server.script(STATUS_ROUTE, httpx.ReadTimeout)
    status_result = under_test.adapter.get_payment_status(ORDER_ID)
    assert status_result.status is GatewayPaymentStatus.NOT_FOUND
    assert len(under_test.server.requests_to(STATUS_ROUTE)) == 2


@pytest.mark.parametrize(
    ("scripted_answers", "expected_error_type"),
    [
        ([httpx.ReadTimeout] * 3, PaymentGatewayTimeoutError),
        ([httpx.Response(503)] * 3, PaymentGatewayUnavailableError),
        ([httpx.ConnectError] * 3, PaymentGatewayTimeoutError),
    ],
    ids=["read-timeouts", "server-errors", "connect-errors"],
)
def test_get_payment_status_failing_every_attempt_raises_typed_error(
    under_test: PaytmAdapterUnderTest,
    scripted_answers: list[httpx.Response | type[httpx.RequestError]],
    expected_error_type: type[PaymentGatewayError],
) -> None:
    """After all retries, timeouts are Timeout and server errors are Unavailable."""
    under_test.server.script(STATUS_ROUTE, *scripted_answers)
    with pytest.raises(expected_error_type):
        under_test.adapter.get_payment_status(ORDER_ID)
    assert len(under_test.server.requests_to(STATUS_ROUTE)) == 3


def build_status_body(order_id: str = ORDER_ID) -> dict[str, Any]:
    """Gives the paid status fixture's body for an order."""
    body: dict[str, Any] = load_fixture("status_txn_success.json")["body"]
    body["orderId"] = order_id
    return body


@pytest.mark.parametrize(
    "reply_text",
    [
        sign_status_reply(build_status_body()).replace('"22000.00"', '"1.00"'),
        '{"head": {"signature": "bm90LWEtc2lnbmF0dXJl"}, "body": {"orderId": "x"}}',
        '{"head": {"signature": 12345}, "body": {"orderId": "x"}}',
        '{"head": {"signature": "bm90LWEtc2lnbmF0dXJl"}}',
    ],
    ids=["body-changed-after-signing", "garbage-signature", "non-text-signature", "no-body"],
)
def test_get_payment_status_with_reply_signature_mismatch_raises_invalid_value(
    under_test: PaytmAdapterUnderTest, reply_text: str
) -> None:
    """A reply whose head signature does not match its exact body text is never trusted."""
    under_test.server.script(STATUS_ROUTE, httpx.Response(200, content=reply_text.encode()))
    with pytest.raises(InvalidPaymentGatewayValueError):
        under_test.adapter.get_payment_status(ORDER_ID)


@pytest.mark.parametrize("head_text", ['"head": {}, ', '"head": null, ', ""])
def test_get_payment_status_without_reply_signature_reads_the_body(
    under_test: PaytmAdapterUnderTest, head_text: str
) -> None:
    """The docs do not say every reply is signed, so an unsigned reply is read [Verify]."""
    reply_text = "{" + head_text + '"body": ' + json.dumps(build_status_body()) + "}"
    under_test.server.script(STATUS_ROUTE, httpx.Response(200, content=reply_text.encode()))
    assert under_test.adapter.get_payment_status(ORDER_ID).status is GatewayPaymentStatus.PAID


def script_signed_status_failure(under_test: PaytmAdapterUnderTest, result_code: str) -> None:
    """Scripts one signed TXN_FAILURE status reply with the given Paytm result code."""
    body: dict[str, Any] = load_fixture("status_txn_failure.json")["body"]
    body["resultInfo"]["resultCode"] = result_code
    under_test.server.script(
        STATUS_ROUTE, httpx.Response(200, content=sign_status_reply(body).encode("utf-8"))
    )


def test_get_payment_status_with_code_501_is_unavailable_and_not_failed(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """ADR 0011 decision 1: Paytm down (501) leaves the status unknown; no FAILED is reported."""
    script_signed_status_failure(under_test, "501")
    with pytest.raises(PaymentGatewayUnavailableError):
        under_test.adapter.get_payment_status(ORDER_ID)


@pytest.mark.parametrize(
    ("result_code", "expected_reason"),
    [
        ("334", PaymentGatewayRejectionReason.INVALID_REQUEST),
        ("335", PaymentGatewayRejectionReason.OPERATION_NOT_PERMITTED),
    ],
    ids=["invalid-order-id-334", "invalid-mid-335"],
)
def test_get_payment_status_with_code_334_or_335_is_a_refusal_and_not_failed(
    under_test: PaytmAdapterUnderTest,
    result_code: str,
    expected_reason: PaymentGatewayRejectionReason,
) -> None:
    """ADR 0011 decision 1: a bad order id or MID is our problem, not a failed payment."""
    script_signed_status_failure(under_test, result_code)
    with pytest.raises(PaymentGatewayRequestRejectedError) as raised:
        under_test.adapter.get_payment_status(ORDER_ID)
    assert raised.value.reason is expected_reason


@pytest.mark.parametrize("result_code", ["227", "401", "235", "295", "810", "820", "843", "267"])
def test_get_payment_status_with_any_other_failure_code_is_failed(
    under_test: PaytmAdapterUnderTest, result_code: str
) -> None:
    """Every remaining documented TXN_FAILURE code still maps the payment to FAILED."""
    script_signed_status_failure(under_test, result_code)
    assert under_test.adapter.get_payment_status(ORDER_ID) == PaymentStatusResult(
        ORDER_ID, GatewayPaymentStatus.FAILED, "SYNTHETIC-TXN-0002", None
    )


def test_verify_webhook_reads_a_genuine_notification(under_test: PaytmAdapterUnderTest) -> None:
    """A webhook signed with our key, for our MID, becomes its event."""
    webhook_event = under_test.adapter.verify_webhook(build_signed_notification())
    assert webhook_event.order_id == ORDER_ID
    assert webhook_event.status is GatewayPaymentStatus.PAID
    assert webhook_event.amount_paid == Money.from_rupees("22000")


@pytest.mark.parametrize(
    "checksum_value", [None, "", "bm90LWEtc2lnbmF0dXJl", "not base64!"], ids=str
)
def test_verify_webhook_with_bad_checksum_raises_before_any_field_is_parsed(
    under_test: PaytmAdapterUnderTest,
    checksum_value: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing or wrong CHECKSUMHASH is rejected and the field mapper is never reached."""

    def refuse_parsing(*_arguments: object) -> None:
        """Fails the test if any field is parsed before the checksum matched."""
        raise AssertionError("fields were parsed before the checksum was verified")

    monkeypatch.setattr(paytm_adapter, "read_webhook_event", refuse_parsing)
    webhook_fields = dict(build_signed_notification(STATUS="NOT-A-STATUS").received_fields)
    webhook_fields.pop("CHECKSUMHASH")
    if checksum_value is not None:
        webhook_fields["CHECKSUMHASH"] = checksum_value
    with pytest.raises(WebhookSignatureInvalidError):
        under_test.adapter.verify_webhook(UnverifiedWebhookNotification(webhook_fields))


def test_verify_webhook_signed_for_another_mid_is_rejected(
    under_test: PaytmAdapterUnderTest,
) -> None:
    """A correctly signed notification for another merchant id is not ours to act on."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        under_test.adapter.verify_webhook(build_signed_notification(MID="SYNTHETICMID00000002"))


def test_paytm_adapter_never_logs_the_merchant_id_vendor_messages_or_personal_data(
    under_test: PaytmAdapterUnderTest, caplog: pytest.LogCaptureFixture
) -> None:
    """With the app's logging set up, retries, refusals and webhooks log no mid or payload."""
    configure_logging("DEBUG")
    under_test.server.script(BANKS_ROUTE, httpx.ReadTimeout)
    under_test.server.script(
        TENURES_ROUTE,
        httpx.Response(200, content=json.dumps(load_fixture("tenures_failure.json")).encode()),
    )
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(PaymentGatewayError):
            under_test.adapter.discover_offers(build_offer_discovery_query())
        under_test.adapter.verify_webhook(build_signed_notification())
    logged_text = caplog.text + " ".join(str(record.__dict__) for record in caplog.records)
    assert caplog.records
    for forbidden_text in (
        SYNTHETIC_MERCHANT_ID,
        "mid=",
        "must never be logged",
        "synthetic.customer@example.test",
        "9999900000",
    ):
        assert forbidden_text not in logged_text
