"""Stores and loads consent one-time code challenges; the code is only ever a keyed hash."""

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.consent import OtpChallenge
from emi_copilot.domain.errors import OtpNotRequestedError
from emi_copilot.models import ConsentOtpChallengeModel


def _to_domain(challenge_model: ConsentOtpChallengeModel) -> OtpChallenge:
    """Maps an ORM row back to a validated domain entity; every moment is returned in UTC."""
    return OtpChallenge(
        id=challenge_model.id,
        customer_session_id=challenge_model.customer_session_id,
        code_hash=challenge_model.code_hash,
        created_at=challenge_model.created_at.astimezone(UTC),
        expires_at=challenge_model.expires_at.astimezone(UTC),
        resend_available_at=challenge_model.resend_available_at.astimezone(UTC),
        attempts_remaining=challenge_model.attempts_remaining,
        verified_at=(
            None
            if challenge_model.verified_at is None
            else challenge_model.verified_at.astimezone(UTC)
        ),
    )


# Pattern: Repository. Keeps challenge queries out of the consent services.
class OtpChallengeRepository:
    """Adds, updates and finds one-time code challenges inside the unit of work's session."""

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for updated_at."""
        self._session = session
        self._clock = clock

    def add(self, otp_challenge: OtpChallenge) -> None:
        """Inserts a new challenge now; created_at is the moment the code was issued."""
        self._session.add(
            ConsentOtpChallengeModel(
                id=otp_challenge.id,
                customer_session_id=otp_challenge.customer_session_id,
                code_hash=otp_challenge.code_hash,
                attempts_remaining=otp_challenge.attempts_remaining,
                expires_at=otp_challenge.expires_at,
                resend_available_at=otp_challenge.resend_available_at,
                verified_at=otp_challenge.verified_at,
                created_at=otp_challenge.created_at,
                updated_at=self._clock.now(),
            )
        )
        self._session.flush()

    def update(self, otp_challenge: OtpChallenge) -> OtpChallenge:
        """Saves the attempts left and the verification moment; returns the stored challenge.

        The code hash, session, lifetime and resend moment never change.
        """
        challenge_model = self._session.get(ConsentOtpChallengeModel, otp_challenge.id)
        if challenge_model is None:
            raise OtpNotRequestedError("No one-time code challenge with this id is stored.")
        challenge_model.attempts_remaining = otp_challenge.attempts_remaining
        challenge_model.verified_at = otp_challenge.verified_at
        challenge_model.updated_at = self._clock.now()
        self._session.flush()
        return _to_domain(challenge_model)

    def find_latest_for_session_for_update(self, customer_session_id: str) -> OtpChallenge | None:
        """Returns the session's most recently issued challenge, locked, or None.

        Ties on the issue moment are broken by id, so the answer is always the same row.
        """
        statement = (
            select(ConsentOtpChallengeModel)
            .where(ConsentOtpChallengeModel.customer_session_id == customer_session_id)
            .order_by(
                ConsentOtpChallengeModel.created_at.desc(), ConsentOtpChallengeModel.id.desc()
            )
            .limit(1)
            .with_for_update()
        )
        challenge_model = self._session.scalars(statement).one_or_none()
        return None if challenge_model is None else _to_domain(challenge_model)
