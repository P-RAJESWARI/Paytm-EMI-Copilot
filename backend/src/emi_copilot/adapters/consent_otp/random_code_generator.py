"""RandomConsentOtpCodeGenerator: unpredictable six-digit codes for a real sender."""

import secrets

from emi_copilot.adapters.consent_otp.code_generator_port import (
    CONSENT_OTP_CODE_DIGIT_COUNT,
    ConsentOtpCodeGenerator,
)

_CODE_COUNT = 10**CONSENT_OTP_CODE_DIGIT_COUNT


# Pattern: Adapter. The generator a real sender pairs with; the factory chooses it once a real
# sender exists. It is built and tested now so that swap is a one-line change.
class RandomConsentOtpCodeGenerator(ConsentOtpCodeGenerator):
    """Draws each code uniformly from 000000 to 999999 with the operating system's randomness."""

    def new_code(self) -> str:
        """Returns a fresh random six-digit code, keeping leading zeros."""
        return f"{secrets.randbelow(_CODE_COUNT):0{CONSENT_OTP_CODE_DIGIT_COUNT}d}"
