"""JSON text for the Paytm adapter: exact bytes out, Decimal-only numbers in, no float anywhere.

Requests are serialised here once, so the text that is signed is exactly the text that is sent.
Money is written as a JSON number with exactly two decimals. Replies are parsed with every JSON
number as Decimal or int, and the raw text of one top-level member can be recovered, because a
reply signature covers the body text exactly as received [Verify].
"""

import json
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money

type JsonRequestValue = (
    str | int | bool | Money | Sequence[JsonRequestValue] | Mapping[str, JsonRequestValue]
)

_RUPEE_AMOUNT_FORMAT = ".2f"
_JSON_WHITESPACE = re.compile(r"[ \t\n\r]*")


def _serialise_money(amount: Money) -> str:
    """Writes whole-paise Money as a JSON number with exactly two decimals, such as 22000.00."""
    if not amount.is_whole_paise:
        raise InvalidPaymentGatewayValueError("Only whole-paise amounts are sent to the gateway.")
    return format(amount.amount_in_rupees, _RUPEE_AMOUNT_FORMAT)


def serialise_json(value: JsonRequestValue) -> str:
    """Writes a request value as compact JSON, keeping mapping order; ASCII-only output."""
    if isinstance(value, Money):
        return _serialise_money(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str | int):
        return json.dumps(value)
    if isinstance(value, Mapping):
        members = (f"{json.dumps(key)}:{serialise_json(item)}" for key, item in value.items())
        return "{" + ",".join(members) + "}"
    return "[" + ",".join(serialise_json(item) for item in value) + "]"


def _reject_non_finite_number(constant_name: str) -> object:
    """Refuses NaN and Infinity, which are not JSON numbers and never a money amount."""
    raise InvalidPaymentGatewayValueError(f"The gateway reply holds {constant_name}.")


def parse_json_object(document_text: str) -> dict[str, object]:
    """Parses a reply that must be a JSON object; every fractional number becomes a Decimal."""
    try:
        document = json.loads(
            document_text, parse_float=Decimal, parse_constant=_reject_non_finite_number
        )
    except json.JSONDecodeError as error:
        raise InvalidPaymentGatewayValueError("The gateway reply is not valid JSON.") from error
    if not isinstance(document, dict):
        raise InvalidPaymentGatewayValueError("The gateway reply is not a JSON object.")
    return document


def _skip_whitespace(document_text: str, position: int) -> int:
    """Gives the first position at or after `position` that is not JSON whitespace."""
    whitespace_match = _JSON_WHITESPACE.match(document_text, position)
    return position if whitespace_match is None else whitespace_match.end()


def _expect_character(document_text: str, position: int, expected_character: str) -> int:
    """Raises unless the expected character is at the position; gives the position after it."""
    if document_text[position : position + 1] != expected_character:
        raise InvalidPaymentGatewayValueError("The gateway reply is not a JSON object.")
    return _skip_whitespace(document_text, position + 1)


def find_raw_top_level_member_text(document_text: str, member_name: str) -> str | None:
    """Gives the exact text of one top-level member's value as received, or None if absent.

    Call it on a reply that parse_json_object has accepted; this scan only finds value bounds.
    With duplicate names the last one wins, as in json.loads, so the text matches what is parsed.
    """
    decoder = json.JSONDecoder(parse_float=Decimal, parse_constant=_reject_non_finite_number)
    position = _expect_character(document_text, _skip_whitespace(document_text, 0), "{")
    member_text: str | None = None
    try:
        while document_text[position : position + 1] != "}":
            if document_text[position : position + 1] != '"':
                raise InvalidPaymentGatewayValueError("The gateway reply is not a JSON object.")
            name, position = decoder.raw_decode(document_text, position)
            position = _expect_character(
                document_text, _skip_whitespace(document_text, position), ":"
            )
            _, value_end = decoder.raw_decode(document_text, position)
            if name == member_name:
                member_text = document_text[position:value_end]
            position = _skip_whitespace(document_text, value_end)
            if document_text[position : position + 1] == ",":
                position = _skip_whitespace(document_text, position + 1)
            elif document_text[position : position + 1] != "}":
                raise InvalidPaymentGatewayValueError("The gateway reply is not a JSON object.")
    except json.JSONDecodeError as error:
        raise InvalidPaymentGatewayValueError("The gateway reply is not valid JSON.") from error
    return member_text
