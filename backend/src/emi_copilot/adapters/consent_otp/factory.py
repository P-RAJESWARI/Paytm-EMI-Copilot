"""ConsentOtpFactory: the one place that pairs the consent code sender with its code generator.

Only the composition root (api/dependencies.py) imports this module (ADR 0008).
"""

from dataclasses import dataclass

from emi_copilot.adapters.consent_otp.code_generator_port import ConsentOtpCodeGenerator
from emi_copilot.adapters.consent_otp.mock_adapter import MockConsentOtpSenderAdapter
from emi_copilot.adapters.consent_otp.mock_code_generator import MockFixedConsentOtpCodeGenerator
from emi_copilot.adapters.consent_otp.port import ConsentOtpSenderPort
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode

PAYTM_MODE_WITHOUT_CONSENT_OTP_SENDER_MESSAGE = (
    "PAYMENT_GATEWAY_MODE=paytm has no real consent one-time code sender yet: only "
    "MockConsentOtpSenderAdapter exists, which sends nothing and accepts the fixed "
    "MOCK_CONSENT_OTP_CODE, so real customers would consent with a known code. Refusing to "
    "start until a real SMS channel exists [Verify with Paytm] (ADR 0004, ADR 0022)."
)


class ConsentOtpConfigurationError(ValueError):
    """Raised at startup when the gateway mode needs a consent code sender that does not exist.

    The message names the settings involved, never the code.
    """


@dataclass(frozen=True, slots=True)
class ConsentOtpComponents:
    """A sender and the generator it must be used with, chosen together."""

    sender: ConsentOtpSenderPort
    code_generator: ConsentOtpCodeGenerator


# Pattern: Factory. Only the labelled Mock sender exists until a real SMS channel is decided. A
# Mock sender delivers nothing, so it always gets the fixed code; a real sender would be paired
# with RandomConsentOtpCodeGenerator here. Like the gateway (ADR 0004), paytm mode never falls
# back to the Mock: startup fails instead.
class ConsentOtpFactory:
    """Builds the consent code sender and generator the application uses."""

    def __init__(self, settings: ApplicationSettings) -> None:
        """Keeps the settings that hold the gateway mode and the Mock's fixed code."""
        self._settings = settings

    def create(self) -> ConsentOtpComponents:
        """Builds the Mock sender and the fixed-code generator; refuses paytm mode."""
        if self._settings.payment_gateway_mode is PaymentGatewayMode.PAYTM:
            raise ConsentOtpConfigurationError(PAYTM_MODE_WITHOUT_CONSENT_OTP_SENDER_MESSAGE)
        return ConsentOtpComponents(
            sender=MockConsentOtpSenderAdapter(),
            code_generator=MockFixedConsentOtpCodeGenerator(
                self._settings.mock_consent_otp_code.get_secret_value()
            ),
        )
