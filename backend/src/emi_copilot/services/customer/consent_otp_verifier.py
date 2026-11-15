"""ConsentOtpVerifier: checks an entered consent code against the session's latest challenge."""

from datetime import datetime

from emi_copilot.core.keyed_hasher import KeyedHasher
from emi_copilot.domain.consent import OtpVerificationAttempt, OtpVerificationOutcome
from emi_copilot.domain.errors import (
    DomainError,
    OtpExpiredError,
    OtpIncorrectError,
    OtpNotRequestedError,
)
from emi_copilot.domain.events import OtpVerificationFailed
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork

OTP_EXPIRED_DETAIL = "This code has expired; request a new code."


class ConsentOtpVerifier:
    """Hashes the entered code for the challenge and compares it, inside the caller's unit of work.

    The code itself is never stored or logged; a wrong code uses one attempt, and after the third
    the code is spent and answers OTP_EXPIRED, never a lockout (ADR 0022 decision 3).
    """

    def __init__(self, keyed_hasher: KeyedHasher, event_bus: DomainEventBus) -> None:
        """Keeps the hasher that binds a code to its challenge and the bus for refused attempts."""
        self._keyed_hasher = keyed_hasher
        self._event_bus = event_bus

    def check(
        self, unit_of_work: UnitOfWork, customer_session_id: str, otp_code: str, now: datetime
    ) -> OtpVerificationAttempt:
        """Checks the code against the session's latest challenge, locked; nothing is saved here."""
        challenge = unit_of_work.otp_challenges.find_latest_for_session_for_update(
            customer_session_id
        )
        if challenge is None:
            raise OtpNotRequestedError("Request a one-time code before agreeing.")
        return challenge.attempt_verification(
            self._keyed_hasher.hash_consent_otp_code(challenge.id, otp_code), now
        )

    def record_refusal(
        self, unit_of_work: UnitOfWork, attempt: OtpVerificationAttempt, now: datetime
    ) -> DomainError:
        """Saves the used attempt, announces the refusal and gives the error to raise later."""
        challenge = unit_of_work.otp_challenges.update(attempt.challenge)
        self._event_bus.publish(
            OtpVerificationFailed(
                occurred_at=now,
                otp_challenge_id=challenge.id,
                customer_session_id=challenge.customer_session_id,
                outcome=attempt.outcome,
                attempts_remaining=challenge.attempts_remaining,
            ),
            unit_of_work,
        )
        if attempt.outcome is OtpVerificationOutcome.INCORRECT:
            return OtpIncorrectError(
                "This code does not match; check it or request a new code.",
                attempts_remaining=challenge.attempts_remaining,
            )
        return OtpExpiredError(OTP_EXPIRED_DETAIL)
