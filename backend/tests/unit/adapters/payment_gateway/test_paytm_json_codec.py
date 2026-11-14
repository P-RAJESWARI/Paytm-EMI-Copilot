"""paytm_json_codec: exact request text with two-decimal rupees, Decimal-only replies."""

import json
from decimal import Decimal

import pytest

from emi_copilot.adapters.payment_gateway.paytm_json_codec import (
    JsonRequestValue,
    find_raw_top_level_member_text,
    parse_json_object,
    serialise_json,
)
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money


@pytest.mark.parametrize(
    ("amount", "expected_text"),
    [
        (Money.from_rupees("22000"), "22000.00"),
        (Money.from_rupees("3666.6"), "3666.60"),
        (Money.from_rupees("0.10"), "0.10"),
        (Money.from_paise(1), "0.01"),
    ],
)
def test_serialise_json_writes_money_as_a_number_with_exactly_two_decimals(
    amount: Money, expected_text: str
) -> None:
    """Rupee amounts are JSON numbers, never strings, always with two decimals."""
    assert serialise_json({"amount": amount}) == '{"amount":' + expected_text + "}"


def test_serialise_json_refuses_sub_paise_money() -> None:
    """An amount below one paisa would be rounded silently, so it is refused."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        serialise_json(Money.from_rupees("1.005"))


def test_serialise_json_writes_compact_ordered_ascii_json() -> None:
    """Keys keep their order, there is no whitespace and non-ASCII text is escaped."""
    request_value: dict[str, JsonRequestValue] = {
        "z": "Bank é",
        "a": [1, True, False, "x"],
        "nested": {"quote": 'say "hi"'},
    }
    serialised_text = serialise_json(request_value)
    assert serialised_text == (
        '{"z":"Bank \\u00e9","a":[1,true,false,"x"],"nested":{"quote":"say \\"hi\\""}}'
    )
    assert json.loads(serialised_text) == request_value


def test_parse_json_object_reads_every_fractional_number_as_decimal() -> None:
    """3666.67 arrives as Decimal("3666.67") exactly; whole numbers stay int."""
    document = parse_json_object('{"emi": 3666.67, "interval": 6, "small": 0.1}')
    assert document == {"emi": Decimal("3666.67"), "interval": 6, "small": Decimal("0.1")}
    assert isinstance(document["emi"], Decimal)
    assert isinstance(document["interval"], int)


@pytest.mark.parametrize(
    "unusable_text",
    ["", "not json", "[1, 2]", '"text"', '{"amount": NaN}', '{"amount": Infinity}'],
)
def test_parse_json_object_refuses_anything_but_a_finite_json_object(unusable_text: str) -> None:
    """Invalid JSON, non-objects and NaN or Infinity are malformed gateway replies."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        parse_json_object(unusable_text)


def test_find_raw_top_level_member_text_keeps_the_value_exactly_as_received() -> None:
    """Whitespace, number spelling and key order inside the value are kept byte for byte."""
    document_text = ' {\n "head" : {"signature": "abc"} ,\n "body":  {"b": 1.50,\n  "a": "x}"}  \n}'
    assert find_raw_top_level_member_text(document_text, "body") == '{"b": 1.50,\n  "a": "x}"}'
    assert find_raw_top_level_member_text(document_text, "head") == '{"signature": "abc"}'


def test_find_raw_top_level_member_text_ignores_nested_names_and_reports_absence() -> None:
    """Only top-level members count; a name inside another value is not a match."""
    document_text = '{"head": {"body": 1}, "other": "body"}'
    assert find_raw_top_level_member_text(document_text, "body") is None
    assert find_raw_top_level_member_text("{}", "body") is None


def test_find_raw_top_level_member_text_with_duplicate_names_takes_the_last_like_json() -> None:
    """json.loads keeps the last duplicate, so the raw text must be that same last one."""
    document_text = '{"body": {"a": 1}, "body": {"a": 2}}'
    assert find_raw_top_level_member_text(document_text, "body") == '{"a": 2}'
    assert json.loads(document_text)["body"] == {"a": 2}


@pytest.mark.parametrize(
    "malformed_text",
    ["[]", '{"body" 1}', '{"body": }', "{1: 2}", '{"body": 1 "x": 2}', '{"body": "open'],
)
def test_find_raw_top_level_member_text_refuses_malformed_documents(malformed_text: str) -> None:
    """A document that is not a well-formed JSON object raises the malformed-reply error."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        find_raw_top_level_member_text(malformed_text, "body")
