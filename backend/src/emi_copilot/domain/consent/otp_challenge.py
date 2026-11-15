"""OtpChallenge entity: one one-time code sent for consent, known only by its keyed hash."""

import hmac
import math
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Self

from emi_copilot.domain.errors import InvalidConsentDataError
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_sha256_hex,
    require_timezone_aware_moment,
)


class OtpVerificationOutcome(StrEnum):
    """What one entered code did to a challenge; the service turns the last two into errors."""

    VERIFIED = "VERIFIED"
    INCORRECT = "INCORRECT"
    """Wrong code, and the challenge still has attempts left (422 OTP_INCORRECT)."""
    EXPIRED = "EXPIRED"
    """Past its lifetime, already used, or this wrong code spent its last attempt (OTP_EXPIRED)."""


@dataclass(frozen=True, slots=True)
class OtpVerificationAttempt:
    """The challenge after one entered code, to be saved, and what that code did."""

    challenge: "OtpChallenge"
    outcome: OtpVerificationOutcome


def _require_moment(value: object, description: str) -> None:
    """Raises unless the value is a timezone-aware datetime."""
    require_timezone_aware_moment(value, description, InvalidConsentDataError)


@dataclass(frozen=True, slots=True)
class OtpChallenge:
    """A one-time code for consent: its keyed hash, lifetime, resend wait and attempts left.

    The code itself is never stored; the hash is computed outside the domain with a secret key, so
    the domain only compares hashes, in constant time. Demo values (3 attempts, 5 minutes, resend
    after 30 seconds) come from settings (ADR 0022 decision 3). It is immutable: each attempt
    returns a new challenge.
    """

    id: str
    customer_session_id: str
    code_hash: str
    created_at: datetime
    expires_at: datetime
    resend_available_at: datetime
    attempts_remaining: int
    verified_at: datetime | None = None

    def __post_init__(self) -> None:
        """Rejects blank ids, a malformed hash, bad moments and a negative attempt count."""
        require_non_empty_text(self.id, "one-time code challenge id", InvalidConsentDataError)
        require_non_empty_text(
            self.customer_session_id, "customer session id", InvalidConsentDataError
        )
        require_sha256_hex(self.code_hash, "one-time code hash", InvalidConsentDataError)
        if isinstance(self.attempts_remaining, bool) or not isinstance(
            self.attempts_remaining, int
        ):
            raise InvalidConsentDataError("The attempts left must be a whole number.")
        if self.attempts_remaining < 0:
            raise InvalidConsentDataError("The attempts left cannot be negative.")
        self._require_consistent_moments()

    def _require_consistent_moments(self) -> None:
        """Raises unless every moment has a time zone and none comes before the challenge."""
        for moment, description in (
            (self.created_at, "challenge start"),
            (self.expires_at, "challenge expiry"),
            (self.resend_available_at, "resend moment"),
        ):
            _require_moment(moment, description)
        if self.expires_at <= self.created_at or self.resend_available_at < self.created_at:
            raise InvalidConsentDataError(
                "A challenge expires, and can be resent, after it starts."
            )
        if self.verified_at is not None:
            _require_moment(self.verified_at, "verification moment")
            if self.verified_at < self.created_at:
                raise InvalidConsentDataError("A challenge cannot be verified before it starts.")

    @classmethod
    def issue(  # noqa: PLR0913 - a new challenge is defined by exactly these facts
        cls,
        *,
        challenge_id: str,
        customer_session_id: str,
        code_hash: str,
        issued_at: datetime,
        lifetime: timedelta,
        resend_wait: timedelta,
        maximum_attempts: int,
    ) -> Self:
        """Issues a challenge with every attempt available, expiring after its lifetime."""
        if isinstance(maximum_attempts, bool) or maximum_attempts < 1:
            raise InvalidConsentDataError("A one-time code allows at least one attempt.")
        return cls(
            id=challenge_id,
            customer_session_id=customer_session_id,
            code_hash=code_hash,
            created_at=issued_at,
            expires_at=issued_at + lifetime,
            resend_available_at=issued_at + resend_wait,
            attempts_remaining=maximum_attempts,
        )

    @property
    def is_spent(self) -> bool:
        """Tells whether every attempt has been used by a wrong code."""
        return self.attempts_remaining == 0

    @property
    def is_verified(self) -> bool:
        """Tells whether a matching code was already entered; a code works only once."""
        return self.verified_at is not None

    def is_expired(self, now: datetime) -> bool:
        """Tells whether the lifetime is over; the expiry moment itself counts as expired."""
        return now >= self.expires_at

    def is_usable(self, now: datetime) -> bool:
        """Tells whether a code may still be checked: in time, not spent and not used."""
        return not (self.is_expired(now) or self.is_spent or self.is_verified)

    def seconds_until_resend(self, now: datetime) -> int:
        """Gives the whole seconds, rounded up, before a new code may be sent; 0 means now."""
        remaining_wait_in_seconds = (self.resend_available_at - now).total_seconds()
        return max(0, math.ceil(remaining_wait_in_seconds))

    def is_matching_code_hash(self, candidate_code_hash: str) -> bool:
        """Compares an entered code's hash with the stored one in constant time."""
        return hmac.compare_digest(candidate_code_hash.encode(), self.code_hash.encode())

    def record_wrong_attempt(self) -> Self:
        """Uses one attempt for a wrong code; a spent challenge has none left to use."""
        if self.is_spent:
            raise InvalidConsentDataError("A spent one-time code has no attempts left.")
        return replace(self, attempts_remaining=self.attempts_remaining - 1)

    def mark_verified(self, now: datetime) -> Self:
        """Records that the matching code was entered now; only a usable challenge can be."""
        if not self.is_usable(now):
            raise InvalidConsentDataError("Only a usable one-time code can be verified.")
        return replace(self, verified_at=now)

    def attempt_verification(
        self, candidate_code_hash: str, now: datetime
    ) -> OtpVerificationAttempt:
        """Checks an entered code's hash, using an attempt when it is wrong (ADR 0022).

        A challenge that is expired, spent or already used is left unchanged. The wrong code that
        uses the last attempt answers EXPIRED, so the screen offers a new code, never a lockout.
        """
        if not self.is_usable(now):
            return OtpVerificationAttempt(self, OtpVerificationOutcome.EXPIRED)
        if self.is_matching_code_hash(candidate_code_hash):
            return OtpVerificationAttempt(self.mark_verified(now), OtpVerificationOutcome.VERIFIED)
        after_wrong_attempt = self.record_wrong_attempt()
        outcome = (
            OtpVerificationOutcome.EXPIRED
            if after_wrong_attempt.is_spent
            else OtpVerificationOutcome.INCORRECT
        )
        return OtpVerificationAttempt(after_wrong_attempt, outcome)
