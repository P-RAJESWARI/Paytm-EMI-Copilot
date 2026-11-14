"""paytm_payload_mapper: v3 status and webhook fields, with card and personal fields dropped."""

import dataclasses
import logging
from typing import Any

import pytest

from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    WEBHOOK_PERSONAL_DATA_FIELDS,
)
from emi_copilot.adapters.payment_gateway.paytm_payload_mapper import (
    read_payment_status,
    read_webhook_event,
)
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    GatewayPaymentStatus,
    PaymentStatusResult,
    VerifiedWebhookEvent,
)
from tests.contract.payment_gateway.paytm_fake_server import SYNTHETIC_MERCHANT_ID, load_fixture

ORDER_ID = "ORDER-SAMPLE-0001"
CARD_LIKE_FIXTURE_VALUES = (
    "SYNTHETIC-CARD-SCHEME",
    "0000",
    "SYNTHETIC-AUTH-CODE",
    "SYNTHETIC-RRN-CODE",
)


def load_status_body(fixture_name: str, **changed_fields: object) -> dict[str, Any]:
    """Gives one status fixture's body with single fields replaced."""
    body: dict[str, Any] = load_fixture(fixture_name)["body"]
    body.update(changed_fields)
    return body


def load_webhook_fields(**changed_fields: str) -> dict[str, str]:
    """Gives the documented webhook fields with single fields replaced."""
    webhook_fields: dict[str, str] = load_fixture("webhook_form_fields.json")
    webhook_fields.update(changed_fields)
    return webhook_fields


def render_every_value(returned_object: object) -> str:
    """Renders every attribute value of a returned dataclass, to search it for leaked data."""
    return " ".join(
        repr(getattr(returned_object, field.name))
        for field in dataclasses.fields(returned_object)  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    ("fixture_name", "expected_result"),
    [
        (
            "status_txn_success.json",
            PaymentStatusResult(
                ORDER_ID,
                GatewayPaymentStatus.PAID,
                "SYNTHETIC-TXN-0001",
                Money.from_rupees("22000"),
            ),
        ),
        (
            "status_pending.json",
            PaymentStatusResult(ORDER_ID, GatewayPaymentStatus.PENDING, None, None),
        ),
        (
            "status_txn_failure.json",
            PaymentStatusResult(ORDER_ID, GatewayPaymentStatus.FAILED, "SYNTHETIC-TXN-0002", None),
        ),
        (
            "status_no_record_found.json",
            PaymentStatusResult(ORDER_ID, GatewayPaymentStatus.NOT_FOUND, None, None),
        ),
    ],
    ids=["txn-success", "pending", "txn-failure", "no-record-found"],
)
def test_read_payment_status_maps_each_documented_result_status(
    fixture_name: str, expected_result: PaymentStatusResult
) -> None:
    """TXN_SUCCESS, PENDING, TXN_FAILURE and NO_RECORD_FOUND map as the facts table says."""
    status_body = load_status_body(fixture_name)
    assert read_payment_status(status_body, ORDER_ID, SYNTHETIC_MERCHANT_ID) == expected_result


def test_read_payment_status_drops_every_card_like_field() -> None:
    """cardScheme, lastFourDigit, authCode and rrnCode never reach the returned result."""
    status_result = read_payment_status(
        load_status_body("status_txn_success.json"), ORDER_ID, SYNTHETIC_MERCHANT_ID
    )
    rendered_values = render_every_value(status_result)
    assert all(value not in rendered_values for value in CARD_LIKE_FIXTURE_VALUES)


def test_read_payment_status_ignores_a_transaction_id_on_an_unknown_order() -> None:
    """An order Paytm does not know has no transaction, even if a stray txnId is sent."""
    status_body = load_status_body("status_no_record_found.json", txnId="SYNTHETIC-TXN-9")
    assert read_payment_status(status_body, ORDER_ID, SYNTHETIC_MERCHANT_ID).status is (
        GatewayPaymentStatus.NOT_FOUND
    )


def test_read_payment_status_accepts_replies_without_order_id_or_mid() -> None:
    """The orderId and mid are compared only when Paytm sends them."""
    status_body = load_status_body("status_pending.json")
    del status_body["orderId"], status_body["mid"]
    assert read_payment_status(status_body, ORDER_ID, SYNTHETIC_MERCHANT_ID).order_id == ORDER_ID


@pytest.mark.parametrize(
    "changed_fields",
    [
        {"orderId": "ORDER-SAMPLE-9999"},
        {"mid": "SYNTHETICMID00000002"},
        {"resultInfo": {"resultStatus": "TXN_UNKNOWN", "resultCode": "01"}},
        {"resultInfo": {"resultCode": "01"}},
        {"txnAmount": None},
        {"txnAmount": "22,000.00"},
        {"txnId": None},
    ],
    ids=[
        "other-order",
        "other-mid",
        "unknown-status",
        "no-status",
        "paid-without-amount",
        "grouped-amount",
        "paid-without-transaction",
    ],
)
def test_read_payment_status_refuses_replies_that_do_not_fit(
    changed_fields: dict[str, object],
) -> None:
    """A reply for another order or merchant, or with an unusable status or amount, raises."""
    status_body = load_status_body("status_txn_success.json", **changed_fields)
    with pytest.raises(InvalidPaymentGatewayValueError):
        read_payment_status(status_body, ORDER_ID, SYNTHETIC_MERCHANT_ID)


def test_read_payment_status_logs_an_undocumented_result_code_by_code_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The status still maps by resultStatus; only the code is logged, never the message."""
    status_body = load_status_body(
        "status_txn_failure.json",
        resultInfo={"resultStatus": "TXN_FAILURE", "resultCode": "999", "resultMsg": "vendor"},
    )
    with caplog.at_level(logging.WARNING):
        status_result = read_payment_status(status_body, ORDER_ID, SYNTHETIC_MERCHANT_ID)
    assert status_result.status is GatewayPaymentStatus.FAILED
    (record,) = caplog.records
    assert record.__dict__["paytm_result_code"] == "999"
    assert "vendor" not in record.getMessage()


def test_read_payment_status_logs_nothing_for_a_documented_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Documented result codes are routine and produce no log event."""
    with caplog.at_level(logging.DEBUG):
        read_payment_status(
            load_status_body("status_pending.json"), ORDER_ID, SYNTHETIC_MERCHANT_ID
        )
    assert caplog.records == []


@pytest.mark.parametrize(
    ("status_value", "expected_status", "expected_amount"),
    [
        ("TXN_SUCCESS", GatewayPaymentStatus.PAID, Money.from_rupees("22000")),
        ("TXN_FAILURE", GatewayPaymentStatus.FAILED, None),
        ("PENDING", GatewayPaymentStatus.PENDING, None),
    ],
)
def test_read_webhook_event_maps_status_and_reads_the_amount_only_when_paid(
    status_value: str, expected_status: GatewayPaymentStatus, expected_amount: Money | None
) -> None:
    """ORDERID, STATUS, TXNID map directly; TXNAMOUNT counts only for a successful payment."""
    webhook_event = read_webhook_event(
        load_webhook_fields(STATUS=status_value), SYNTHETIC_MERCHANT_ID
    )
    assert webhook_event == VerifiedWebhookEvent(
        ORDER_ID, expected_status, "SYNTHETIC-TXN-0001", expected_amount
    )


def test_read_webhook_event_never_returns_personal_fields() -> None:
    """PAYMENTEMAILID and PAYMENTMOBILENUMBER are never part of the returned event."""
    webhook_fields = load_webhook_fields()
    personal_values = [webhook_fields[field_name] for field_name in WEBHOOK_PERSONAL_DATA_FIELDS]
    webhook_event = read_webhook_event(webhook_fields, SYNTHETIC_MERCHANT_ID)
    rendered_values = render_every_value(webhook_event) + repr(webhook_event)
    assert personal_values == [value for value in personal_values if value]
    assert all(value not in rendered_values for value in personal_values)


def test_read_webhook_event_reads_an_empty_transaction_id_as_none() -> None:
    """A failed payment with no TXNID has no gateway transaction id."""
    webhook_event = read_webhook_event(
        load_webhook_fields(STATUS="TXN_FAILURE", TXNID=""), SYNTHETIC_MERCHANT_ID
    )
    assert webhook_event.gateway_transaction_id is None


@pytest.mark.parametrize(
    "changed_fields",
    [
        {"MID": "SYNTHETICMID00000002"},
        {"MID": ""},
        {"STATUS": "NO_RECORD_FOUND"},
        {"STATUS": "SUCCESS"},
        {"ORDERID": ""},
        {"TXNAMOUNT": "abc"},
    ],
    ids=["other-mid", "no-mid", "not-found", "unknown-status", "no-order", "bad-amount"],
)
def test_read_webhook_event_refuses_fields_that_do_not_fit(changed_fields: dict[str, str]) -> None:
    """Another merchant's MID, an unknown status, no order id or a bad amount raises."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        read_webhook_event(load_webhook_fields(**changed_fields), SYNTHETIC_MERCHANT_ID)


def test_read_webhook_event_without_mid_or_status_raises() -> None:
    """MID and STATUS are required; a webhook missing either is refused."""
    for missing_field in ("MID", "STATUS"):
        webhook_fields = load_webhook_fields()
        del webhook_fields[missing_field]
        with pytest.raises(InvalidPaymentGatewayValueError):
            read_webhook_event(webhook_fields, SYNTHETIC_MERCHANT_ID)
