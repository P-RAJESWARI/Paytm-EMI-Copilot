"""ConsentOtpFactory: the one place that pairs the consent code sender with its code generator.

Only the composition root (api/dependencies.py) imports this module (ADR 0008).
"""

from dataclasses import dataclass

from emi_copilot.adapters.consent_otp.code_generator_port import ConsentOtpCodeGenerator
from emi_copilot.adapters.consent_otp.mock_adapter import MockConsentOtpSenderAdapter
from emi_copilot.adapters.consent_otp.mock_code_generator import MockFixedConsentOtpCodeGenerator
from emi_copilot.adapters.consent_otp.port import ConsentOtpSenderPort
from emi_copilot.config.settings import ApplicationSettings


@dataclass(frozen=True, slots=True)
class ConsentOtpComponents:
    """A sender and the generator it must be used with, chosen together."""

    sender: ConsentOtpSenderPort
    code_generator: ConsentOtpCodeGenerator


# Pattern: Factory. Only the labelled Mock sender exists until a real SMS channel is decided, so
# there is no mode setting yet. A Mock sender delivers nothing, so it always gets the fixed code;
# a real sender would be paired with RandomConsentOtpCodeGenerator here.
class ConsentOtpFactory:
    """Builds the consent code sender and generator the application uses."""

    def __init__(self, settings: ApplicationSettings) -> None:
        """Keeps the settings that hold the Mock's fixed code."""
        self._settings = settings

    def create(self) -> ConsentOtpComponents:
        """Builds the Mock sender, which announces itself, and the fixed-code generator."""
        return ConsentOtpComponents(
            sender=MockConsentOtpSenderAdapter(),
            code_generator=MockFixedConsentOtpCodeGenerator(
                self._settings.mock_consent_otp_code.get_secret_value()
            ),
        )
