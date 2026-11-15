"""ConsentOtpService: sends the one-time code that confirms consent (C9)."""

from datetime import timedelta

from emi_copilot.adapters.consent_otp.code_generator_port import ConsentOtpCodeGenerator
from emi_copilot.adapters.consent_otp.port import ConsentOtpSenderPort
from emi_copilot.adapters.customer_contact.port import CustomerContactPort
from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.keyed_hasher import KeyedHasher
from emi_copilot.domain.consent import CustomerPhoneNumber, OtpChallenge
from emi_copilot.domain.customer_sessions import CustomerSession
from emi_copilot.domain.errors import CustomerContactUnavailableError, OtpResendNotYetAvailableError
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.customer.consent_types import IssuedOtpChallenge
from emi_copilot.services.customer.customer_session_access import (
    CustomerSessionAccess,
    require_confirmed_budget,
)
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.sale_expiry import SaleExpiryStep


def require_customer_phone_number(
    customer_contact: CustomerContactPort, sale_id: str
) -> CustomerPhoneNumber:
    """Gives the sale's phone number from the payment side; raises when it knows none."""
    phone_number = customer_contact.find_customer_phone_number(sale_id)
    if phone_number is None:
        raise CustomerContactUnavailableError(
            "No phone number is known for this sale; ask the shop for help."
        )
    return phone_number


class ConsentOtpService:
    """Issues a new consent challenge and sends its code; the code and number stay in memory.

    The number comes from CustomerContactPort (ADR 0022 decision 2) and is used only to send the
    code. A usable code cannot be replaced until its resend wait is over (429 with Retry-After);
    an expired, spent or used one can be replaced at once.
    """

    def __init__(  # noqa: PLR0913 - a use case wired with its collaborators, by keyword
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        id_generator: IdGenerator,
        sale_expiry: SaleExpiryStep,
        customer_contact: CustomerContactPort,
        code_generator: ConsentOtpCodeGenerator,
        code_sender: ConsentOtpSenderPort,
        keyed_hasher: KeyedHasher,
        otp_lifetime: timedelta,
        otp_resend_wait: timedelta,
        otp_maximum_attempts: int,
    ) -> None:
        """Keeps the collaborators and the demo code rules from settings (ADR 0022 decision 3)."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._id_generator = id_generator
        self._session_access = CustomerSessionAccess(sale_expiry)
        self._customer_contact = customer_contact
        self._code_generator = code_generator
        self._code_sender = code_sender
        self._keyed_hasher = keyed_hasher
        self._otp_lifetime = otp_lifetime
        self._otp_resend_wait = otp_resend_wait
        self._otp_maximum_attempts = otp_maximum_attempts

    def request_otp(self, credentials: CustomerSessionCredentials) -> IssuedOtpChallenge:
        """Sends a new code for an active session with a confirmed budget on a CHOOSING sale."""
        session = self._read_session_ready_for_consent(credentials)
        phone_number = require_customer_phone_number(self._customer_contact, session.sale_id)
        challenge_id = self._id_generator.new_id()
        code = self._code_generator.new_code()
        with self._unit_of_work_factory() as unit_of_work:
            now = self._clock.now()
            # Locking the session row makes two requests from one phone take turns.
            unit_of_work.customer_sessions.find_by_id_for_update(session.id)
            latest = unit_of_work.otp_challenges.find_latest_for_session_for_update(session.id)
            if latest is not None and latest.is_usable(now):
                seconds_to_wait = latest.seconds_until_resend(now)
                if seconds_to_wait > 0:
                    raise OtpResendNotYetAvailableError(
                        seconds_to_wait, "A new code can be sent once the wait is over."
                    )
            challenge = OtpChallenge.issue(
                challenge_id=challenge_id,
                customer_session_id=session.id,
                code_hash=self._keyed_hasher.hash_consent_otp_code(challenge_id, code),
                issued_at=now,
                lifetime=self._otp_lifetime,
                resend_wait=self._otp_resend_wait,
                maximum_attempts=self._otp_maximum_attempts,
            )
            unit_of_work.otp_challenges.add(challenge)
        self._code_sender.send(phone_number, code)
        return IssuedOtpChallenge(
            phone_last_two_digits=phone_number.last_two_digits,
            expires_at=challenge.expires_at,
            resend_available_at=challenge.resend_available_at,
            attempts_remaining=challenge.attempts_remaining,
        )

    def _read_session_ready_for_consent(
        self, credentials: CustomerSessionCredentials
    ) -> CustomerSession:
        """Gives the session while its sale is CHOOSING and its budget confirmed; else raises."""
        with self._unit_of_work_factory() as unit_of_work:
            opened = self._session_access.open_sale(unit_of_work, credentials, self._clock.now())
            refusal = opened.find_choosing_refusal()
            if refusal is None:
                require_confirmed_budget(opened.session)
                return opened.session
        raise refusal
