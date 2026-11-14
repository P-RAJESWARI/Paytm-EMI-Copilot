"""Maps Paytm reply bodies and webhook fields into domain types through an explicit whitelist.

Only the fields named in paytm_api_definitions are read. Everything else, including card-like
fields (cardScheme, lastFourDigit, authCode, rrnCode), the vendor's messages and the webhook's
PAYMENTEMAILID and PAYMENTMOBILENUMBER, is never read, so it cannot leave the adapter. Shapes
that do not fit raise InvalidPaymentGatewayValueError.
"""

import logging
from collections.abc import Mapping

from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    BANK_CODE_FIELD,
    BANK_DETAILS_FIELD,
    BANK_NAME_FIELD,
    CARD_TYPE_FIELD,
    CARD_TYPES_FIELD,
    DOCUMENTED_RESULT_CODES_BY_RESULT_STATUS,
    EMI_TYPES_FIELD,
    GRATIFICATION_TYPE_FIELD,
    GRATIFICATION_VALUE_FIELD,
    KNOWN_CARD_TYPES,
    KNOWN_GRATIFICATION_TYPES,
    KNOWN_PLAN_TYPES,
    LINK_ID_FIELD,
    MERCHANT_ID_FIELD,
    PLAN_DETAILS_FIELD,
    PLAN_EMI_FIELD,
    PLAN_EMI_TYPE_FIELD,
    PLAN_GRATIFICATIONS_FIELD,
    PLAN_ID_FIELD,
    PLAN_INTEREST_FIELD,
    PLAN_INTERVAL_FIELD,
    SHORT_URL_FIELD,
    STATUS_ORDER_ID_FIELD,
    STATUS_TRANSACTION_AMOUNT_FIELD,
    STATUS_TRANSACTION_ID_FIELD,
    SUBVENTION_PLAN_TYPE,
    TRANSACTION_STATUSES_BY_RESULT_STATUS,
    WEBHOOK_MERCHANT_ID_FIELD,
    WEBHOOK_ORDER_ID_FIELD,
    WEBHOOK_STATUS_FIELD,
    WEBHOOK_STATUSES_BY_STATUS_VALUE,
    WEBHOOK_TRANSACTION_AMOUNT_FIELD,
    WEBHOOK_TRANSACTION_ID_FIELD,
)
from emi_copilot.adapters.payment_gateway.paytm_request_builder import BankCardPair
from emi_copilot.adapters.payment_gateway.paytm_response_values import (
    JsonObject,
    read_identifier,
    read_object,
    read_objects,
    read_optional_object,
    read_optional_text,
    read_result_info,
    read_rupee_amount,
    read_text,
    read_whole_months,
)
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    EmiOffer,
    EmiType,
    GatewayPaymentStatus,
    PaymentLink,
    PaymentStatusResult,
    VerifiedWebhookEvent,
)

paytm_payload_mapper_logger = logging.getLogger(__name__)
_NO_EXTRA = Money.from_paise(0)


def _read_known_value(container: JsonObject, field_name: str, known_values: frozenset[str]) -> str:
    """Reads a text field whose value must be one of the documented values."""
    value = read_text(container, field_name)
    if value not in known_values:
        raise InvalidPaymentGatewayValueError(
            f"The gateway reply field {field_name!r} holds an undocumented value."
        )
    return value


def _read_pairs_of_one_emi_type(emi_type_entry: JsonObject) -> list[BankCardPair]:
    """Reads one emiTypes entry, literally: a cardTypes array beside one bankDetails [Verify]."""
    bank_code = read_text(read_object(emi_type_entry, BANK_DETAILS_FIELD), BANK_CODE_FIELD)
    return [
        BankCardPair(
            bank_code, _read_known_value(card_type_entry, CARD_TYPE_FIELD, KNOWN_CARD_TYPES)
        )
        for card_type_entry in read_objects(emi_type_entry, CARD_TYPES_FIELD)
    ]


def read_bank_card_pairs(banks_body: JsonObject) -> tuple[BankCardPair, ...]:
    """Lists each distinct bank and card type with EMI, in reply order, from the Banks body."""
    distinct_pairs: dict[BankCardPair, None] = {}
    for emi_type_entry in read_objects(banks_body, EMI_TYPES_FIELD):
        for bank_card_pair in _read_pairs_of_one_emi_type(emi_type_entry):
            distinct_pairs.setdefault(bank_card_pair)
    return tuple(distinct_pairs)


def calculate_net_extra_in_total(interest: Money, gratification_value: Money) -> Money:
    """Gives interest minus the gratification, never below zero (ADR 0010 section 2)."""
    if gratification_value >= interest:
        return _NO_EXTRA
    return interest - gratification_value


def _read_gratification_value(plan: JsonObject) -> Money:
    """Reads a subvention plan's gratification value; no gratification counts as zero [Verify]."""
    gratification = read_optional_object(plan, PLAN_GRATIFICATIONS_FIELD)
    if gratification is None:
        return _NO_EXTRA
    _read_known_value(gratification, GRATIFICATION_TYPE_FIELD, KNOWN_GRATIFICATION_TYPES)
    return read_rupee_amount(gratification, GRATIFICATION_VALUE_FIELD)


def _read_offer(plan: JsonObject, lender_label: str) -> EmiOffer:
    """Turns one planDetails entry into an offer; NO_COST exactly when the net extra is zero."""
    interest = read_rupee_amount(plan, PLAN_INTEREST_FIELD)
    is_subvention_plan = (
        _read_known_value(plan, PLAN_EMI_TYPE_FIELD, KNOWN_PLAN_TYPES) == SUBVENTION_PLAN_TYPE
    )
    gratification_value = _read_gratification_value(plan) if is_subvention_plan else _NO_EXTRA
    net_extra_in_total = calculate_net_extra_in_total(interest, gratification_value)
    return EmiOffer(
        offer_id=read_identifier(plan, PLAN_ID_FIELD),
        lender_label=lender_label,
        emi_type=EmiType.NO_COST if net_extra_in_total.is_zero else EmiType.STANDARD,
        tenure_in_months=read_whole_months(plan, PLAN_INTERVAL_FIELD),
        quoted_monthly_installment=read_rupee_amount(plan, PLAN_EMI_FIELD),
        quoted_extra_in_total=net_extra_in_total,
    )


def read_tenure_offers(tenures_body: JsonObject) -> tuple[EmiOffer, ...]:
    """Turns every plan in a Tenures body into an offer from that body's bank; none is dropped."""
    lender_label = read_text(tenures_body, BANK_NAME_FIELD)
    return tuple(
        _read_offer(plan, lender_label) for plan in read_objects(tenures_body, PLAN_DETAILS_FIELD)
    )


def read_payment_link(link_body: JsonObject, order_id: str) -> PaymentLink:
    """Reads the link id and the short URL shared with the customer; the long URL is never read."""
    return PaymentLink(
        order_id=order_id,
        gateway_link_id=read_identifier(link_body, LINK_ID_FIELD),
        payment_url=read_text(link_body, SHORT_URL_FIELD),
    )


def _require_matching_value(
    container: JsonObject, field_name: str, expected_value: str, *, is_required: bool
) -> None:
    """Raises when a field differs from what we expect; an absent optional field is accepted."""
    received_value = read_optional_text(container, field_name)
    if received_value is None and not is_required:
        return
    if received_value != expected_value:
        raise InvalidPaymentGatewayValueError(
            f"The gateway reply field {field_name!r} does not match our request."
        )


def _read_transaction_status(status_body: JsonObject) -> GatewayPaymentStatus:
    """Maps resultStatus to our status and logs, by code only, a result code not documented."""
    result_info = read_result_info(status_body)
    status = TRANSACTION_STATUSES_BY_RESULT_STATUS.get(result_info.result_status)
    if status is None:
        raise InvalidPaymentGatewayValueError("The transaction status is not a documented value.")
    documented_codes = DOCUMENTED_RESULT_CODES_BY_RESULT_STATUS[result_info.result_status]
    if result_info.result_code not in documented_codes:
        paytm_payload_mapper_logger.warning(
            "paytm transaction status result code undocumented",
            extra={"paytm_result_code": result_info.result_code},
        )
    return status


def read_payment_status(
    status_body: JsonObject, order_id: str, merchant_id: str
) -> PaymentStatusResult:
    """Reads the v3 status body for our order: status, transaction id and, if paid, the amount."""
    _require_matching_value(status_body, STATUS_ORDER_ID_FIELD, order_id, is_required=False)
    _require_matching_value(status_body, MERCHANT_ID_FIELD, merchant_id, is_required=False)
    status = _read_transaction_status(status_body)
    is_paid = status is GatewayPaymentStatus.PAID
    return PaymentStatusResult(
        order_id=order_id,
        status=status,
        gateway_transaction_id=(
            None
            if status is GatewayPaymentStatus.NOT_FOUND
            else read_optional_text(status_body, STATUS_TRANSACTION_ID_FIELD)
        ),
        amount_paid=(
            read_rupee_amount(status_body, STATUS_TRANSACTION_AMOUNT_FIELD) if is_paid else None
        ),
    )


def read_webhook_event(
    verified_fields: Mapping[str, str], merchant_id: str
) -> VerifiedWebhookEvent:
    """Reads a webhook whose checksum already matched: our MID first, then the payment fields.

    ORDERID is the linkOrderId we sent, which is our order id [Verify]. The amount is read only
    for a successful payment; personal fields are never touched.
    """
    _require_matching_value(
        verified_fields, WEBHOOK_MERCHANT_ID_FIELD, merchant_id, is_required=True
    )
    status = WEBHOOK_STATUSES_BY_STATUS_VALUE.get(verified_fields.get(WEBHOOK_STATUS_FIELD, ""))
    if status is None:
        raise InvalidPaymentGatewayValueError("The webhook status is not a documented value.")
    is_paid = status is GatewayPaymentStatus.PAID
    return VerifiedWebhookEvent(
        order_id=read_text(verified_fields, WEBHOOK_ORDER_ID_FIELD),
        status=status,
        gateway_transaction_id=read_optional_text(verified_fields, WEBHOOK_TRANSACTION_ID_FIELD),
        amount_paid=(
            read_rupee_amount(verified_fields, WEBHOOK_TRANSACTION_AMOUNT_FIELD)
            if is_paid
            else None
        ),
    )
