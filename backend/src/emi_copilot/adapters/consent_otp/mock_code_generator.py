"""MockFixedConsentOtpCodeGenerator: the same demo code every time, for the Mock sender."""

import re

from emi_copilot.adapters.consent_otp.code_generator_port import (
    CONSENT_OTP_CODE_DIGIT_COUNT,
    ConsentOtpCodeGenerator,
)

_CODE_PATTERN = re.compile(rf"[0-9]{{{CONSENT_OTP_CODE_DIGIT_COUNT}}}")


# Pattern: Adapter (Mock). Nothing is sent in the demo, so the customer types a known code
# (MOCK_CONSENT_OTP_CODE); it is documented in the handoff and never logged (ADR 0022).
class MockFixedConsentOtpCodeGenerator(ConsentOtpCodeGenerator):
    """Gives one configured six-digit code for every challenge."""

    def __init__(self, fixed_code: str) -> None:
        """Keeps the fixed code, which must be exactly six digits; the message never echoes it."""
        if _CODE_PATTERN.fullmatch(fixed_code) is None:
            raise ValueError("The Mock consent code must be exactly six digits.")
        self._fixed_code = fixed_code

    def new_code(self) -> str:
        """Returns the fixed demo code."""
        return self._fixed_code

    def __repr__(self) -> str:
        """Names the class only, so the code never reaches a log through repr."""
        return "MockFixedConsentOtpCodeGenerator(code=<hidden>)"
