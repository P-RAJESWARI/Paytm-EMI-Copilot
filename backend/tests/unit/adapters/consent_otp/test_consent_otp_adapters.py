"""The OTP Mock sends nothing and logs no code or number; generators give six-digit codes."""

import logging

import pytest
from pydantic import SecretStr

from emi_copilot.adapters.consent_otp import random_code_generator
from emi_copilot.adapters.consent_otp.factory import ConsentOtpFactory
from emi_copilot.adapters.consent_otp.mock_adapter import (
    MOCK_CONSENT_OTP_SENDER_ACTIVE_WARNING,
    MOCK_CONSENT_OTP_SENT_MESSAGE,
    MockConsentOtpSenderAdapter,
)
from emi_copilot.adapters.consent_otp.mock_code_generator import MockFixedConsentOtpCodeGenerator
from emi_copilot.adapters.consent_otp.random_code_generator import RandomConsentOtpCodeGenerator
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.domain.consent import CustomerPhoneNumber

SYNTHETIC_PHONE_NUMBER = CustomerPhoneNumber("9000000042")


def test_factory_pairs_the_mock_sender_with_the_configured_fixed_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A Mock sender delivers nothing, so it always gets the code the customer is told to type."""
    settings = ApplicationSettings(mock_consent_otp_code=SecretStr("654321"))
    with caplog.at_level(logging.WARNING):
        components = ConsentOtpFactory(settings).create()
    assert isinstance(components.sender, MockConsentOtpSenderAdapter)
    assert components.sender.adapter_name == "mock"
    assert isinstance(components.code_generator, MockFixedConsentOtpCodeGenerator)
    assert components.code_generator.new_code() == "654321"
    assert [record.getMessage() for record in caplog.records] == [
        MOCK_CONSENT_OTP_SENDER_ACTIVE_WARNING
    ]
    assert "654321" not in caplog.text


def test_mock_sender_logs_the_event_but_never_the_code_or_any_digit_of_the_number(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Never log OTPs or phone numbers (security-and-compliance.md section 3)."""
    sender = MockConsentOtpSenderAdapter()
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        sender.send(SYNTHETIC_PHONE_NUMBER, "123456")
    (record,) = caplog.records
    assert record.getMessage() == MOCK_CONSENT_OTP_SENT_MESSAGE
    logged_text = f"{caplog.text} {record.__dict__}"
    for forbidden_text in ("123456", "9000000042", "ending 42"):
        assert forbidden_text not in logged_text


@pytest.mark.parametrize("fixed_code", ["12345", "1234567", "12345a", ""])
def test_fixed_generator_refuses_anything_but_six_digits_with_a_fixed_message(
    fixed_code: str,
) -> None:
    """The consent screen asks for exactly six digits."""
    with pytest.raises(ValueError, match=r"^The Mock consent code must be exactly six digits\.$"):
        MockFixedConsentOtpCodeGenerator(fixed_code)


def test_fixed_generator_repr_hides_the_code() -> None:
    """A stray log of the generator cannot leak the demo code."""
    assert "123456" not in repr(MockFixedConsentOtpCodeGenerator("123456"))


def test_random_generator_gives_six_digits_with_leading_zeros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A small draw is padded, so every code has six digits."""
    monkeypatch.setattr(f"{random_code_generator.__name__}.secrets.randbelow", lambda _bound: 42)
    assert RandomConsentOtpCodeGenerator().new_code() == "000042"


def test_random_generator_codes_are_six_digit_strings() -> None:
    """Real draws are always six digits."""
    generator = RandomConsentOtpCodeGenerator()
    assert all(
        len(code) == 6 and code.isdigit() for code in (generator.new_code() for _ in range(100))
    )
