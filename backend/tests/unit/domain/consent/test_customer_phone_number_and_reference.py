"""CustomerPhoneNumber keeps the number out of logs; ConsentReference is EMI-DDMM-NNNN."""

from datetime import date

import pytest

from emi_copilot.domain.consent import ConsentReference, CustomerPhoneNumber
from emi_copilot.domain.errors import InvalidConsentDataError

# Synthetic, clearly fictional numbers; never a real customer's.
SYNTHETIC_NATIONAL_NUMBER = "9000000042"


@pytest.mark.parametrize("written_number", [SYNTHETIC_NATIONAL_NUMBER, "+919000000042"])
def test_phone_number_normalises_to_ten_digits_and_shows_only_the_last_two(
    written_number: str,
) -> None:
    """The +91 prefix is dropped; only "ending 42" ever appears when it is printed."""
    phone_number = CustomerPhoneNumber(written_number)
    assert phone_number.national_number == SYNTHETIC_NATIONAL_NUMBER
    assert phone_number.last_two_digits == "42"
    assert repr(phone_number) == "CustomerPhoneNumber(ending 42)"
    assert SYNTHETIC_NATIONAL_NUMBER not in f"{phone_number} {phone_number!r}"


@pytest.mark.parametrize(
    "written_number",
    ["5000000042", "900000004", "90000000421", "+18000000042", "90000-00042", 9000000042],
    ids=["starts-with-5", "nine-digits", "eleven-digits", "other-country", "dash", "integer"],
)
def test_phone_number_refuses_anything_but_an_indian_mobile_without_echoing_it(
    written_number: object,
) -> None:
    """The error detail never repeats the number."""
    with pytest.raises(InvalidConsentDataError) as raised_error:
        CustomerPhoneNumber(written_number)  # type: ignore[arg-type]
    assert "0042" not in raised_error.value.detail


def test_consent_reference_for_consent_day_matches_the_design_receipt() -> None:
    """26 November with serial 42 gives the design's EMI-2611-0042."""
    assert ConsentReference.for_consent_day(date(2026, 11, 26), 42).value == "EMI-2611-0042"
    assert ConsentReference.for_consent_day(date(2027, 1, 5), 0).value == "EMI-0501-0000"
    assert ConsentReference.for_consent_day(date(2027, 12, 31), 9999).value == "EMI-3112-9999"


@pytest.mark.parametrize("serial_number", [-1, 10_000, True, "42"])
def test_consent_reference_refuses_serial_numbers_outside_four_digits(
    serial_number: object,
) -> None:
    """The serial is a whole number from 0 to 9999."""
    with pytest.raises(InvalidConsentDataError):
        ConsentReference.for_consent_day(date(2026, 11, 26), serial_number)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    ["EMI-2611-042", "EMI-0011-0042", "EMI-3211-0042", "EMI-2613-0042", "emi-2611-0042", 2611],
)
def test_consent_reference_refuses_malformed_values(value: object) -> None:
    """A stored reference must be shaped EMI-DDMM-NNNN with a real day and month number."""
    with pytest.raises(InvalidConsentDataError):
        ConsentReference(value)  # type: ignore[arg-type]
