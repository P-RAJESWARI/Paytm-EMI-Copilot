"""MockConsentOtpSenderAdapter: "sent" means only logged as sent; nothing leaves the process."""

import logging

from emi_copilot.adapters.consent_otp.port import ConsentOtpSenderPort
from emi_copilot.domain.consent import CustomerPhoneNumber

MOCK_CONSENT_OTP_SENDER_ADAPTER_NAME = "mock"
MOCK_CONSENT_OTP_SENDER_ACTIVE_WARNING = (
    "MockConsentOtpSenderAdapter active: consent codes are never sent; customers type the "
    "fixed MOCK_CONSENT_OTP_CODE"
)
MOCK_CONSENT_OTP_SENT_MESSAGE = "mock consent one-time code sent"

mock_consent_otp_sender_logger = logging.getLogger(__name__)


# Pattern: Adapter (Mock). A labelled stand-in for an SMS channel (CLAUDE.md section 2, rule 10).
class MockConsentOtpSenderAdapter(ConsentOtpSenderPort):
    """Sends nothing; logs only that a code was "sent", never the code or the number."""

    def __init__(self) -> None:
        """Announces in the startup log that consent codes are mocked."""
        mock_consent_otp_sender_logger.warning(
            MOCK_CONSENT_OTP_SENDER_ACTIVE_WARNING,
            extra={"consent_otp_sender_adapter": MOCK_CONSENT_OTP_SENDER_ADAPTER_NAME},
        )

    @property
    def adapter_name(self) -> str:
        """Gives "mock"."""
        return MOCK_CONSENT_OTP_SENDER_ADAPTER_NAME

    def send(self, phone_number: CustomerPhoneNumber, code: str) -> None:  # noqa: ARG002 - never sent
        """Logs the event alone: no code, no number, not even its last digits."""
        mock_consent_otp_sender_logger.info(MOCK_CONSENT_OTP_SENT_MESSAGE)
