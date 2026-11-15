"""Doubles of the customer flow's ports: profile, phone number, code delivery and sources."""

from dataclasses import dataclass, field

from emi_copilot.adapters.consent_otp.code_generator_port import ConsentOtpCodeGenerator
from emi_copilot.adapters.consent_otp.port import ConsentOtpSenderPort
from emi_copilot.adapters.customer_contact.port import CustomerContactPort
from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.core.opaque_token import IssuedOpaqueToken, hash_opaque_token
from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.consent import CustomerPhoneNumber
from emi_copilot.domain.money import Money

SYNTHETIC_PHONE_NUMBER = CustomerPhoneNumber("9000000042")
OTP_CODE = "123456"
CONSENT_REFERENCE_SERIAL = 42
STANDARD_PROFILE = FinancialProfile(
    monthly_inflow=Money.from_rupees(30000), existing_emis_per_month=Money.from_rupees(8000)
)
"""The design's customer: inflow ₹30,000, existing EMIs ₹8,000 (synthetic)."""


class SequentialSessionTokenIssuer:
    """Issues predictable session tokens, so a test can present the one it was given."""

    def __init__(self) -> None:
        """Starts counting at zero."""
        self._issued_count = 0

    def __call__(self) -> IssuedOpaqueToken:
        """Returns the next numbered token with its hash."""
        self._issued_count += 1
        token = f"synthetic-session-token-{self._issued_count:04d}"
        return IssuedOpaqueToken(token=token, token_hash=hash_opaque_token(token))


@dataclass
class RecordingFinancialProfilePort(FinancialProfilePort):
    """Gives the standard synthetic profile and records which sessions asked."""

    customer_session_ids: list[str] = field(default_factory=list)

    def get_financial_profile(self, customer_session_id: str) -> FinancialProfile:
        """Records the session id and gives the standard profile."""
        self.customer_session_ids.append(customer_session_id)
        return STANDARD_PROFILE


@dataclass
class FakeCustomerContact(CustomerContactPort):
    """Gives one synthetic number for every sale, or none when a test removes it."""

    phone_number: CustomerPhoneNumber | None = SYNTHETIC_PHONE_NUMBER

    @property
    def adapter_name(self) -> str:
        """Gives "fake"."""
        return "fake"

    def find_customer_phone_number(self, sale_id: str) -> CustomerPhoneNumber | None:  # noqa: ARG002 - one number for all
        """Gives the scripted number."""
        return self.phone_number


@dataclass
class RecordingConsentOtpSender(ConsentOtpSenderPort):
    """Records the last two digits and the code of every send; delivers nothing."""

    sent: list[tuple[str, str]] = field(default_factory=list)

    @property
    def adapter_name(self) -> str:
        """Gives "fake"."""
        return "fake"

    def send(self, phone_number: CustomerPhoneNumber, code: str) -> None:
        """Records the send."""
        self.sent.append((phone_number.last_two_digits, code))


class FixedConsentOtpCodeGenerator(ConsentOtpCodeGenerator):
    """Always gives OTP_CODE, so a test can type it."""

    def new_code(self) -> str:
        """Returns OTP_CODE."""
        return OTP_CODE


class FixedConsentReferenceSerialGenerator:
    """Always gives serial 42, as in the design's EMI-2611-0042."""

    def new_serial_number(self) -> int:
        """Returns 42."""
        return CONSENT_REFERENCE_SERIAL
