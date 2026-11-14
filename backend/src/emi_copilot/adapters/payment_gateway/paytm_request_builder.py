"""Builds Paytm request heads and bodies from our domain types; no card or contact field exists.

Amounts are Money, written by paytm_json_codec as JSON numbers with two decimals. The envelope is
assembled from the body text that was signed, so the signed bytes are the bytes sent.
"""

from dataclasses import dataclass

from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    BODY_FIELD,
    CUSTOMER_ID_FIELD,
    FILTER_BANK_CODE_FIELD,
    FILTER_CARD_TYPE_FIELD,
    FILTERS_FIELD,
    FIXED_LINK_TYPE,
    HEAD_FIELD,
    HEAD_REQUEST_ID_FIELD,
    HEAD_REQUEST_TIMESTAMP_FIELD,
    HEAD_SIGNATURE_FIELD,
    HEAD_TOKEN_FIELD,
    HEAD_TOKEN_TYPE_FIELD,
    HEAD_VERSION_FIELD,
    HEAD_VERSION_VALUE,
    ITEM_BRAND_ID_FIELD,
    ITEM_CATEGORY_LIST_FIELD,
    ITEM_ID_FIELD,
    ITEM_PRICE_FIELD,
    ITEM_PRODUCT_ID_FIELD,
    ITEM_QUANTITY_FIELD,
    ITEMS_FIELD,
    LINK_AMOUNT_FIELD,
    LINK_DESCRIPTION_FIELD,
    LINK_NAME_FIELD,
    LINK_ORDER_ID_FIELD,
    LINK_ORDER_ID_MAXIMUM_LENGTH,
    LINK_TOKEN_TYPE_VALUE,
    LINK_TYPE_FIELD,
    MERCHANT_ID_FIELD,
    REQUEST_ID_MAXIMUM_LENGTH,
    SELECT_PLAN_ON_CASHIER_PAGE_FIELD,
    SIMPLIFIED_SUBVENTION_FIELD,
    STATUS_CALLBACK_URL_FIELD,
    STATUS_ORDER_ID_FIELD,
    SUBVENTION_TOKEN_TYPE_VALUE,
)
from emi_copilot.adapters.payment_gateway.paytm_json_codec import JsonRequestValue, serialise_json
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery, PaymentLinkRequest

JsonRequestObject = dict[str, JsonRequestValue]

# One item per sale; its id is our product id, since the item list holds a single line [Verify].
SINGLE_ITEM_QUANTITY = 1
# Our own non-personal wording. With an order id of at most 50 characters the name stays within
# 64 and the description within 30, Paytm's documented lengths (tested).
LINK_NAME_PREFIX = "EMI order "
LINK_DESCRIPTION_TEXT = "EMI payment for your purchase"


@dataclass(frozen=True, slots=True)
class BankCardPair:
    """One bank and card type that the Banks API offers EMI for; Tenures is asked per pair."""

    bank_code: str
    card_type: str


def build_items(
    price: Money, product_id: str, brand_id: str, category_id: str
) -> list[JsonRequestValue]:
    """Builds the single-item list; the price is the item price times its quantity of one."""
    return [
        {
            ITEM_ID_FIELD: product_id,
            ITEM_PRODUCT_ID_FIELD: product_id,
            ITEM_BRAND_ID_FIELD: brand_id,
            ITEM_CATEGORY_LIST_FIELD: [category_id],
            ITEM_PRICE_FIELD: price * SINGLE_ITEM_QUANTITY,
            ITEM_QUANTITY_FIELD: SINGLE_ITEM_QUANTITY,
        }
    ]


def build_banks_request_body(merchant_id: str, query: OfferDiscoveryQuery) -> JsonRequestObject:
    """Builds the Banks body: our merchant id and the item; nothing about the customer or card."""
    return {
        MERCHANT_ID_FIELD: merchant_id,
        ITEMS_FIELD: build_items(query.price, query.product_id, query.brand_id, query.category_id),
    }


def build_tenures_request_body(
    merchant_id: str, query: OfferDiscoveryQuery, bank_card_pair: BankCardPair
) -> JsonRequestObject:
    """Builds the Tenures body for one bank and card type; it never carries a card number or BIN."""
    return {
        **build_banks_request_body(merchant_id, query),
        FILTERS_FIELD: {
            FILTER_BANK_CODE_FIELD: bank_card_pair.bank_code,
            FILTER_CARD_TYPE_FIELD: bank_card_pair.card_type,
        },
    }


def build_create_link_request_body(
    merchant_id: str, request: PaymentLinkRequest, status_callback_url: str | None
) -> JsonRequestObject:
    """Builds a FIXED link for our order with item-based subvention; plan chosen on Paytm's page.

    partialPayment, bindLinkIdMobile and every contact, SMS or email field are left out on
    purpose (ADR 0010 section 1).
    """
    if len(request.order_id) > LINK_ORDER_ID_MAXIMUM_LENGTH:
        raise InvalidPaymentGatewayValueError(
            f"The order id must be at most {LINK_ORDER_ID_MAXIMUM_LENGTH} characters for a link."
        )
    body: JsonRequestObject = {
        MERCHANT_ID_FIELD: merchant_id,
        LINK_NAME_FIELD: LINK_NAME_PREFIX + request.order_id,
        LINK_DESCRIPTION_FIELD: LINK_DESCRIPTION_TEXT,
        LINK_TYPE_FIELD: FIXED_LINK_TYPE,
        LINK_AMOUNT_FIELD: request.amount,
        LINK_ORDER_ID_FIELD: request.order_id,
    }
    if status_callback_url is not None:
        body[STATUS_CALLBACK_URL_FIELD] = status_callback_url
    body[SIMPLIFIED_SUBVENTION_FIELD] = {
        CUSTOMER_ID_FIELD: request.customer_reference,
        ITEMS_FIELD: build_items(
            request.amount, request.product_id, request.brand_id, request.category_id
        ),
        SELECT_PLAN_ON_CASHIER_PAGE_FIELD: True,
    }
    return body


def build_status_request_body(merchant_id: str, order_id: str) -> JsonRequestObject:
    """Builds the v3 status body: merchant id and our order id only; txnType is never sent."""
    return {MERCHANT_ID_FIELD: merchant_id, STATUS_ORDER_ID_FIELD: order_id}


def build_subvention_head(request_id: str, request_timestamp: str, token: str) -> JsonRequestObject:
    """Builds the Banks and Tenures head around the body checksum."""
    if len(request_id) > REQUEST_ID_MAXIMUM_LENGTH:
        raise InvalidPaymentGatewayValueError(
            f"A request id must be at most {REQUEST_ID_MAXIMUM_LENGTH} characters."
        )
    return {
        HEAD_REQUEST_ID_FIELD: request_id,
        HEAD_REQUEST_TIMESTAMP_FIELD: request_timestamp,
        HEAD_VERSION_FIELD: HEAD_VERSION_VALUE,
        HEAD_TOKEN_TYPE_FIELD: SUBVENTION_TOKEN_TYPE_VALUE,
        HEAD_TOKEN_FIELD: token,
    }


def build_link_head(signature: str) -> JsonRequestObject:
    """Builds the Create Link head around the body signature; the optional timestamp is omitted."""
    return {HEAD_TOKEN_TYPE_FIELD: LINK_TOKEN_TYPE_VALUE, HEAD_SIGNATURE_FIELD: signature}


def build_status_head(signature: str) -> JsonRequestObject:
    """Builds the v3 status head around the body signature; optional fields are omitted."""
    return {HEAD_SIGNATURE_FIELD: signature}


def build_envelope_text(head: JsonRequestObject, signed_body_text: str) -> str:
    """Wraps the exact signed body text and the head as {"head": ..., "body": ...}."""
    return (
        "{"
        + f"{serialise_json(HEAD_FIELD)}:{serialise_json(head)},"
        + f"{serialise_json(BODY_FIELD)}:{signed_body_text}"
        + "}"
    )
