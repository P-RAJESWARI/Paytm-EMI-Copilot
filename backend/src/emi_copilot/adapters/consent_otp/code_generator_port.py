"""ConsentOtpCodeGenerator: where a new consent one-time code comes from."""

from abc import ABC, abstractmethod

CONSENT_OTP_CODE_DIGIT_COUNT = 6
"""C9 asks for a six-digit code."""


# Pattern: Port and Adapter. A Mock sender delivers nothing, so it must be paired with the fixed
# Mock code the customer is told to type; a real sender pairs with random codes.
class ConsentOtpCodeGenerator(ABC):
    """Gives the six-digit code for a new challenge; the code is never logged or stored."""

    @abstractmethod
    def new_code(self) -> str:
        """Returns a code of exactly six digits."""
