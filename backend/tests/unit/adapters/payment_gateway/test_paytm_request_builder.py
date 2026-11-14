"""paytm_request_builder: exact request bodies with no card, contact or partial-payment field."""

import json
from decimal import Decimal

import pytest

from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    LINK_DESCRIPTION_MAXIMUM_LENGTH,
    LINK_NAME_MAXIMUM_LENGTH,
)
from emi_copilot.adapters.payment_gateway.paytm_json_codec import serialise_json
from emi_copilot.adapters.payment_gateway.paytm_request_builder import (
    LINK_DESCRIPTION_TEXT,
    BankCardPair,
    build_banks_request_body,
    build_create_link_request_body,
    build_envelope_text,
    build_status_request_body,
    build_subvention_head,
    build_tenures_request_body,
)
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from tests.contract.payment_gateway.paytm_fake_server import SYNTHETIC_MERCHANT_ID
from tests.payment_builders import build_offer_discovery_query, build_payment_link_request

SAMPLE_ITEMS_TEXT = (
    '[{"id":"product-sample-0001","productId":"product-sample-0001",'
    '"brandId":"brand-sample-0001","categoryList":["category-sample-0001"],'
    '"price":22000.00,"quantity":1}]'
)
CALLBACK_URL = "https://emi-copilot.example.test/api/v1/webhooks/paytm"
CARD_OR_CONTACT_WORDS = ("card", "bin", "cvv", "expiry", "mobile", "phone", "email", "sms")


def collect_all_keys(value: object) -> set[str]:
    """Lists every key at any depth of a parsed JSON value."""
    if isinstance(value, dict):
        return set(value).union(*(collect_all_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(collect_all_keys(item) for item in value))
    return set()


def test_build_banks_request_body_is_merchant_id_and_one_item_with_two_decimal_price() -> None:
    """The Banks body is exactly the documented fields, with the rupee price as 22000.00."""
    body_text = serialise_json(
        build_banks_request_body(SYNTHETIC_MERCHANT_ID, build_offer_discovery_query())
    )
    assert body_text == '{"mid":"SYNTHETICMID00000001","items":' + SAMPLE_ITEMS_TEXT + "}"


def test_build_tenures_request_body_adds_only_the_bank_and_card_type_filter() -> None:
    """Tenures asks for one bank and card type; no card number or BIN is ever sent."""
    body = build_tenures_request_body(
        SYNTHETIC_MERCHANT_ID, build_offer_discovery_query(), BankCardPair("DEMOA", "CREDIT_CARD")
    )
    assert serialise_json(body) == (
        '{"mid":"SYNTHETICMID00000001","items":'
        + SAMPLE_ITEMS_TEXT
        + ',"filters":{"bankCode":"DEMOA","cardType":"CREDIT_CARD"}}'
    )


def test_build_create_link_request_body_is_a_fixed_item_based_subvention_link() -> None:
    """FIXED link, our order id as linkOrderId, plan chosen on Paytm's page, our webhook URL."""
    request = build_payment_link_request()
    body = json.loads(
        serialise_json(
            build_create_link_request_body(SYNTHETIC_MERCHANT_ID, request, CALLBACK_URL)
        ),
        parse_float=Decimal,
    )
    assert body == {
        "mid": SYNTHETIC_MERCHANT_ID,
        "linkName": "EMI order ORDER-SAMPLE-0001",
        "linkDescription": "EMI payment for your purchase",
        "linkType": "FIXED",
        "amount": Decimal("22000.00"),
        "linkOrderId": "ORDER-SAMPLE-0001",
        "statusCallbackUrl": CALLBACK_URL,
        "simplifiedSubvention": {
            "customerId": request.customer_reference,
            "items": json.loads(SAMPLE_ITEMS_TEXT, parse_float=Decimal),
            "selectPlanOnCashierPage": True,
        },
    }


def test_build_create_link_request_body_never_sends_partial_payment_mobile_or_card_fields() -> None:
    """ADR 0010: no partialPayment, no bindLinkIdMobile, no contact, SMS, email or card field."""
    body = build_create_link_request_body(
        SYNTHETIC_MERCHANT_ID, build_payment_link_request(), CALLBACK_URL
    )
    all_keys = {key.lower() for key in collect_all_keys(json.loads(serialise_json(body)))}
    assert "partialpayment" not in all_keys
    assert "bindlinkidmobile" not in all_keys
    assert not [key for key in all_keys for word in CARD_OR_CONTACT_WORDS if word in key]


def test_build_create_link_request_body_without_callback_url_omits_it() -> None:
    """With no webhook URL configured, statusCallbackUrl is left out instead of sent empty."""
    body = build_create_link_request_body(SYNTHETIC_MERCHANT_ID, build_payment_link_request(), None)
    assert "statusCallbackUrl" not in body


def test_build_create_link_request_body_keeps_link_texts_within_documented_lengths() -> None:
    """A 50-character order id still gives a name of at most 64 and a description of 30."""
    longest_order_id = "O" * 50
    body = build_create_link_request_body(
        SYNTHETIC_MERCHANT_ID, build_payment_link_request(order_id=longest_order_id), None
    )
    assert len(str(body["linkName"])) <= LINK_NAME_MAXIMUM_LENGTH
    assert len(LINK_DESCRIPTION_TEXT) <= LINK_DESCRIPTION_MAXIMUM_LENGTH


def test_build_create_link_request_body_refuses_an_order_id_paytm_cannot_hold() -> None:
    """The linkOrderId holds at most 50 characters; a longer order id is refused before sending."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        build_create_link_request_body(
            SYNTHETIC_MERCHANT_ID, build_payment_link_request(order_id="O" * 51), None
        )


def test_build_status_request_body_is_merchant_id_and_order_id_only() -> None:
    """The v3 status body carries mid and orderId; txnType is never sent."""
    assert serialise_json(build_status_request_body(SYNTHETIC_MERCHANT_ID, "ORDER-1")) == (
        '{"mid":"SYNTHETICMID00000001","orderId":"ORDER-1"}'
    )


def test_build_subvention_head_refuses_a_request_id_longer_than_32_characters() -> None:
    """The requestId is string(32); a longer generated id is refused rather than truncated."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        build_subvention_head("R" * 33, "1794652200", "token-text")


def test_build_envelope_text_embeds_the_signed_body_text_unchanged() -> None:
    """The envelope holds the head and exactly the body text that was signed, body last."""
    signed_body_text = '{"mid":"SYNTHETICMID00000001", "spacing":"kept"}'
    envelope_text = build_envelope_text({"signature": "sig"}, signed_body_text)
    assert envelope_text == '{"head":{"signature":"sig"},"body":' + signed_body_text + "}"
