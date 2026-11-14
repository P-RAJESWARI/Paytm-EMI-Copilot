"""Typed readers for single values in a parsed Paytm reply; anything unexpected is rejected.

Every reader names the field in its error but never echoes the received value, so no vendor
payload can travel inside an exception. Numbers arrive as Decimal or int (paytm_json_codec), and
Paytm sends some amounts as text, so rupee amounts accept all three forms [Verify].
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    RESULT_CODE_FIELD,
    RESULT_INFO_FIELD,
    RESULT_STATUS_FIELD,
)
from emi_copilot.domain.errors import InvalidMoneyAmountError, InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money

JsonObject = Mapping[str, object]


def _missing_or_malformed(field_name: str) -> InvalidPaymentGatewayValueError:
    """Builds the error for a field that is absent or of the wrong shape, naming the field only."""
    return InvalidPaymentGatewayValueError(
        f"The gateway reply field {field_name!r} is missing or malformed."
    )


def read_object(container: JsonObject, field_name: str) -> JsonObject:
    """Reads a field that must hold a JSON object."""
    value = container.get(field_name)
    if not isinstance(value, Mapping):
        raise _missing_or_malformed(field_name)
    return value


def read_optional_object(container: JsonObject, field_name: str) -> JsonObject | None:
    """Reads a field that may be absent or null, and otherwise must hold a JSON object."""
    if container.get(field_name) is None:
        return None
    return read_object(container, field_name)


def read_objects(container: JsonObject, field_name: str) -> tuple[JsonObject, ...]:
    """Reads a field that must hold an array of JSON objects; an empty array is allowed."""
    value = container.get(field_name)
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise _missing_or_malformed(field_name)
    return tuple(value)


def read_text(container: JsonObject, field_name: str) -> str:
    """Reads a field that must hold non-blank text."""
    value = container.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise _missing_or_malformed(field_name)
    return value


def read_optional_text(container: JsonObject, field_name: str) -> str | None:
    """Reads a field that may be absent, null or empty text (all meaning absent), else text."""
    value = container.get(field_name)
    if value is None or value == "":
        return None
    return read_text(container, field_name)


def read_identifier(container: JsonObject, field_name: str) -> str:
    """Reads an id Paytm may send as text or as a whole number; both become text."""
    value = container.get(field_name)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return read_text(container, field_name)


def read_whole_months(container: JsonObject, field_name: str) -> int:
    """Reads a tenure that must be a JSON whole number (bools and decimals are refused)."""
    value = container.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _missing_or_malformed(field_name)
    return value


def parse_rupee_amount(value: object, field_name: str) -> Money:
    """Turns a rupee amount sent as Decimal, int or plain decimal text into whole-paise Money."""
    if isinstance(value, bool) or not isinstance(value, Decimal | int | str):
        raise _missing_or_malformed(field_name)
    try:
        amount = Money.from_rupees(value)
    except InvalidMoneyAmountError as error:
        raise _missing_or_malformed(field_name) from error
    if not amount.is_whole_paise:
        raise _missing_or_malformed(field_name)
    return amount


def read_rupee_amount(container: JsonObject, field_name: str) -> Money:
    """Reads a field that must hold a rupee amount in whole paise."""
    return parse_rupee_amount(container.get(field_name), field_name)


@dataclass(frozen=True, slots=True)
class PaytmResultInfo:
    """The status word and result code of a reply; the vendor's message is never kept."""

    result_status: str
    result_code: str


def read_result_info(container: JsonObject) -> PaytmResultInfo:
    """Reads resultInfo's status and code; a missing code reads as empty text, for logging only."""
    result_info = read_object(container, RESULT_INFO_FIELD)
    result_code = result_info.get(RESULT_CODE_FIELD)
    is_whole_number = isinstance(result_code, int) and not isinstance(result_code, bool)
    return PaytmResultInfo(
        result_status=read_text(result_info, RESULT_STATUS_FIELD),
        result_code=(str(result_code) if is_whole_number or isinstance(result_code, str) else ""),
    )
