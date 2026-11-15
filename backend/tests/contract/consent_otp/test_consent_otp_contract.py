"""ConsentOtpSenderPort and ConsentOtpCodeGenerator contracts (only the labelled Mock sender).

A real SMS sender joins the sender parametrisation with recorded fixtures when one is decided;
both code generators are run here already, since the factory chooses between them.
"""

import logging
from collections.abc import Callable

import pytest

from emi_copilot.adapters.consent_otp.code_generator_port import (
    CONSENT_OTP_CODE_DIGIT_COUNT,
    ConsentOtpCodeGenerator,
)
from emi_copilot.adapters.consent_otp.mock_adapter import MockConsentOtpSenderAdapter
from emi_copilot.adapters.consent_otp.mock_code_generator import MockFixedConsentOtpCodeGenerator
from emi_copilot.adapters.consent_otp.port import ConsentOtpSenderPort
from emi_copilot.adapters.consent_otp.random_code_generator import RandomConsentOtpCodeGenerator
from emi_copilot.domain.consent import CustomerPhoneNumber

CONSENT_OTP_SENDER_BUILDERS: dict[str, Callable[[], ConsentOtpSenderPort]] = {
    "mock": MockConsentOtpSenderAdapter,
}
CONSENT_OTP_CODE_GENERATOR_BUILDERS: dict[str, Callable[[], ConsentOtpCodeGenerator]] = {
    "mock-fixed": lambda: MockFixedConsentOtpCodeGenerator("123456"),
    "random": RandomConsentOtpCodeGenerator,
}
SYNTHETIC_PHONE_NUMBER = CustomerPhoneNumber("9000000042")


@pytest.fixture(params=sorted(CONSENT_OTP_SENDER_BUILDERS))
def consent_otp_sender(request: pytest.FixtureRequest) -> ConsentOtpSenderPort:
    """Builds each sender in turn."""
    builder: Callable[[], ConsentOtpSenderPort] = CONSENT_OTP_SENDER_BUILDERS[request.param]
    return builder()


@pytest.fixture(params=sorted(CONSENT_OTP_CODE_GENERATOR_BUILDERS))
def consent_otp_code_generator(request: pytest.FixtureRequest) -> ConsentOtpCodeGenerator:
    """Builds each code generator in turn."""
    builder: Callable[[], ConsentOtpCodeGenerator] = CONSENT_OTP_CODE_GENERATOR_BUILDERS[
        request.param
    ]
    return builder()


def test_sender_accepts_a_code_and_never_logs_it_or_the_number(
    consent_otp_sender: ConsentOtpSenderPort, caplog: pytest.LogCaptureFixture
) -> None:
    """Sending returns nothing, and no log line carries the code or the phone number."""
    with caplog.at_level(logging.DEBUG):
        consent_otp_sender.send(SYNTHETIC_PHONE_NUMBER, "123456")
    assert "123456" not in caplog.text
    assert "9000000042" not in caplog.text


def test_sender_names_itself(consent_otp_sender: ConsentOtpSenderPort) -> None:
    """The name is announced at startup."""
    assert consent_otp_sender.adapter_name


def test_code_generator_gives_six_digit_codes(
    consent_otp_code_generator: ConsentOtpCodeGenerator,
) -> None:
    """Every code is exactly the six digits C9 asks for."""
    for _ in range(20):
        code = consent_otp_code_generator.new_code()
        assert len(code) == CONSENT_OTP_CODE_DIGIT_COUNT
        assert code.isdigit()
