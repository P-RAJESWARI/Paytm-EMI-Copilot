"""paytm_response_values: each reader accepts its documented forms and rejects everything else."""

from decimal import Decimal

import pytest

from emi_copilot.adapters.payment_gateway.paytm_response_values import (
    PaytmResultInfo,
    parse_rupee_amount,
    read_identifier,
    read_object,
    read_objects,
    read_optional_object,
    read_optional_text,
    read_result_info,
    read_text,
    read_whole_months,
)
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money


@pytest.mark.parametrize(
    ("received_value", "expected_amount"),
    [
        (Decimal("3666.67"), Money.from_rupees("3666.67")),
        (22000, Money.from_rupees("22000")),
        ("2050.00", Money.from_rupees("2050")),
        (Decimal("1E+3"), Money.from_rupees("1000")),
        (Decimal("0.10"), Money.from_rupees("0.1")),
    ],
)
def test_parse_rupee_amount_accepts_decimal_int_and_plain_text(
    received_value: object, expected_amount: Money
) -> None:
    """Paytm mixes numbers and text for amounts; all become exact whole-paise Money."""
    assert parse_rupee_amount(received_value, "emi") == expected_amount


@pytest.mark.parametrize(
    "unusable_value",
    [
        None,
        True,
        3666.67,
        Decimal("-1"),
        Decimal("1.005"),
        "-5.00",
        "1,000.00",
        "",
        [1],
    ],
    ids=[
        "none",
        "bool",
        "float",
        "negative",
        "sub-paise",
        "negative-text",
        "grouped",
        "empty",
        "list",
    ],
)
def test_parse_rupee_amount_refuses_floats_and_malformed_amounts(unusable_value: object) -> None:
    """A float, bool, negative, sub-paise or formatted amount is a malformed reply."""
    with pytest.raises(InvalidPaymentGatewayValueError) as raised:
        parse_rupee_amount(unusable_value, "emi")
    assert "'emi'" in raised.value.detail


def test_readers_name_the_field_but_never_echo_the_received_value() -> None:
    """Errors carry the field name only, so no vendor payload travels inside an exception."""
    with pytest.raises(InvalidPaymentGatewayValueError) as raised:
        read_whole_months({"interval": "SECRET-LOOKING-VALUE"}, "interval")
    assert "SECRET-LOOKING-VALUE" not in str(raised.value)


def test_read_object_and_objects_require_the_json_shapes() -> None:
    """Objects must be objects and arrays must hold only objects; empty arrays are fine."""
    assert read_object({"a": {"b": 1}}, "a") == {"b": 1}
    assert read_objects({"a": [{"b": 1}]}, "a") == ({"b": 1},)
    assert read_objects({"a": []}, "a") == ()
    for container in ({"a": [1]}, {"a": {"b": 1}}, {}):
        with pytest.raises(InvalidPaymentGatewayValueError):
            read_objects(container, "a")
    with pytest.raises(InvalidPaymentGatewayValueError):
        read_object({"a": [1]}, "a")


def test_read_optional_object_reads_absent_and_null_as_none() -> None:
    """A missing or null optional object is None; a non-object is still malformed."""
    assert read_optional_object({}, "a") is None
    assert read_optional_object({"a": None}, "a") is None
    with pytest.raises(InvalidPaymentGatewayValueError):
        read_optional_object({"a": "x"}, "a")


def test_text_readers_treat_blank_as_missing_and_empty_optional_as_absent() -> None:
    """Required text must be non-blank; optional text reads absent, null and "" as None."""
    assert read_text({"a": "x"}, "a") == "x"
    assert read_optional_text({}, "a") is None
    assert read_optional_text({"a": None}, "a") is None
    assert read_optional_text({"a": ""}, "a") is None
    for container in ({"a": " "}, {"a": 1}, {}):
        with pytest.raises(InvalidPaymentGatewayValueError):
            read_text(container, "a")
    with pytest.raises(InvalidPaymentGatewayValueError):
        read_optional_text({"a": " "}, "a")


def test_read_identifier_accepts_text_or_whole_numbers_only() -> None:
    """Ids arrive as text or numbers and always leave as text; bools and decimals are refused."""
    assert read_identifier({"id": 90000001}, "id") == "90000001"
    assert read_identifier({"id": "SYNTHETIC-1"}, "id") == "SYNTHETIC-1"
    for unusable_id in (True, Decimal("1.5"), None):
        with pytest.raises(InvalidPaymentGatewayValueError):
            read_identifier({"id": unusable_id}, "id")


def test_read_whole_months_accepts_json_integers_only() -> None:
    """A tenure is a JSON whole number; text, decimals and bools are refused."""
    assert read_whole_months({"interval": 6}, "interval") == 6
    for unusable_interval in ("6", Decimal("6.0"), True):
        with pytest.raises(InvalidPaymentGatewayValueError):
            read_whole_months({"interval": unusable_interval}, "interval")


@pytest.mark.parametrize(
    ("result_code", "expected_code"),
    [("5028", "5028"), (200, "200"), (None, ""), (True, ""), (Decimal("1.0"), "")],
)
def test_read_result_info_keeps_status_and_code_but_never_the_message(
    result_code: object, expected_code: str
) -> None:
    """The code is kept as text for logging; anything else reads as empty; no message is kept."""
    container = {
        "resultInfo": {"resultStatus": "F", "resultCode": result_code, "resultMsg": "vendor text"}
    }
    assert read_result_info(container) == PaytmResultInfo("F", expected_code)
