"""OtpChallenge: three attempts, a five-minute lifetime, a resend wait and single use (ADR 0022)."""

from datetime import datetime, timedelta

import pytest

from emi_copilot.domain.consent import OtpChallenge, OtpVerificationOutcome
from emi_copilot.domain.errors import InvalidConsentDataError
from tests.consent_builders import (
    OTP_CHALLENGE_ID,
    SESSION_STARTED_AT,
    SYNTHETIC_OTP_CODE_HASH,
    build_otp_challenge,
)

WRONG_CODE_HASH = "e" * 64
SOON = SESSION_STARTED_AT + timedelta(minutes=1)


def test_issue_gives_every_attempt_a_lifetime_and_a_resend_wait() -> None:
    """A new code allows 3 attempts, expires after 5 minutes and can be resent after 30 seconds."""
    otp_challenge = build_otp_challenge()
    assert otp_challenge.id == OTP_CHALLENGE_ID
    assert otp_challenge.attempts_remaining == 3
    assert otp_challenge.expires_at == SESSION_STARTED_AT + timedelta(minutes=5)
    assert otp_challenge.resend_available_at == SESSION_STARTED_AT + timedelta(seconds=30)
    assert otp_challenge.verified_at is None
    assert otp_challenge.is_usable(SESSION_STARTED_AT)


@pytest.mark.parametrize("maximum_attempts", [0, True])
def test_issue_refuses_fewer_than_one_attempt(maximum_attempts: int) -> None:
    """A code that cannot be tried at all is a configuration error."""
    with pytest.raises(InvalidConsentDataError):
        OtpChallenge.issue(
            challenge_id=OTP_CHALLENGE_ID,
            customer_session_id="session",
            code_hash=SYNTHETIC_OTP_CODE_HASH,
            issued_at=SESSION_STARTED_AT,
            lifetime=timedelta(minutes=5),
            resend_wait=timedelta(seconds=30),
            maximum_attempts=maximum_attempts,
        )


def test_matching_code_verifies_the_challenge_once() -> None:
    """The right code is accepted, and the same challenge cannot be used again."""
    verification = build_otp_challenge().attempt_verification(SYNTHETIC_OTP_CODE_HASH, SOON)
    assert verification.outcome is OtpVerificationOutcome.VERIFIED
    assert verification.challenge.verified_at == SOON
    assert verification.challenge.is_verified
    replay = verification.challenge.attempt_verification(SYNTHETIC_OTP_CODE_HASH, SOON)
    assert replay.outcome is OtpVerificationOutcome.EXPIRED
    assert replay.challenge is verification.challenge


def test_wrong_codes_count_down_and_the_third_spends_the_challenge() -> None:
    """Two wrong codes leave 2 then 1 attempt; the third answers EXPIRED, never a lockout."""
    otp_challenge = build_otp_challenge()
    outcomes_and_attempts_left = []
    for _ in range(3):
        verification = otp_challenge.attempt_verification(WRONG_CODE_HASH, SOON)
        otp_challenge = verification.challenge
        outcomes_and_attempts_left.append((verification.outcome, otp_challenge.attempts_remaining))
    assert outcomes_and_attempts_left == [
        (OtpVerificationOutcome.INCORRECT, 2),
        (OtpVerificationOutcome.INCORRECT, 1),
        (OtpVerificationOutcome.EXPIRED, 0),
    ]
    assert otp_challenge.is_spent
    after_spent = otp_challenge.attempt_verification(SYNTHETIC_OTP_CODE_HASH, SOON)
    assert after_spent.outcome is OtpVerificationOutcome.EXPIRED
    assert after_spent.challenge is otp_challenge


def test_a_code_entered_at_or_after_expiry_is_expired_and_uses_no_attempt() -> None:
    """Even the right code is refused once the lifetime is over."""
    otp_challenge = build_otp_challenge()
    assert not otp_challenge.is_expired(otp_challenge.expires_at - timedelta(microseconds=1))
    assert otp_challenge.is_expired(otp_challenge.expires_at)
    verification = otp_challenge.attempt_verification(
        SYNTHETIC_OTP_CODE_HASH, otp_challenge.expires_at
    )
    assert verification.outcome is OtpVerificationOutcome.EXPIRED
    assert verification.challenge.attempts_remaining == 3


def test_record_wrong_attempt_on_a_spent_challenge_raises() -> None:
    """A spent challenge has no attempt left to use."""
    with pytest.raises(InvalidConsentDataError):
        build_otp_challenge(attempts_remaining=0).record_wrong_attempt()


def test_mark_verified_refuses_a_challenge_that_is_not_usable() -> None:
    """An expired code cannot be marked verified."""
    otp_challenge = build_otp_challenge()
    with pytest.raises(InvalidConsentDataError):
        otp_challenge.mark_verified(otp_challenge.expires_at)


@pytest.mark.parametrize(
    ("seconds_after_issue", "expected_wait_in_seconds"),
    [(0, 30), (29.5, 1), (30, 0), (45, 0)],
)
def test_seconds_until_resend_rounds_up_and_is_zero_once_the_wait_is_over(
    seconds_after_issue: float, expected_wait_in_seconds: int
) -> None:
    """The Retry-After value is whole seconds rounded up, so a resend is never refused early."""
    now = SESSION_STARTED_AT + timedelta(seconds=seconds_after_issue)
    assert build_otp_challenge().seconds_until_resend(now) == expected_wait_in_seconds


def test_is_matching_code_hash_compares_the_whole_hash() -> None:
    """Only the identical hash matches."""
    otp_challenge = build_otp_challenge()
    assert otp_challenge.is_matching_code_hash(SYNTHETIC_OTP_CODE_HASH)
    assert not otp_challenge.is_matching_code_hash(SYNTHETIC_OTP_CODE_HASH[:-1] + "0")


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": ""},
        {"customer_session_id": " "},
        {"code_hash": "123456"},
        {"attempts_remaining": -1},
        {"attempts_remaining": True},
        {"attempts_remaining": "3"},
        {"created_at": datetime(2026, 11, 26, 9, 30)},  # noqa: DTZ001 - a naive moment on purpose
        {"expires_at": SESSION_STARTED_AT},
        {"resend_available_at": SESSION_STARTED_AT - timedelta(seconds=1)},
        {"verified_at": datetime(2026, 11, 26, 9, 31)},  # noqa: DTZ001 - a naive moment on purpose
        {"verified_at": SESSION_STARTED_AT - timedelta(seconds=1)},
    ],
    ids=[
        "blank-id",
        "blank-session",
        "plain-code-not-hash",
        "negative-attempts",
        "bool-attempts",
        "text-attempts",
        "naive-start",
        "expiry-at-start",
        "resend-before-start",
        "naive-verification",
        "verified-before-start",
    ],
)
def test_otp_challenge_refuses_inconsistent_fields(overrides: dict[str, object]) -> None:
    """Invalid challenges cannot be built, so a repository can never load one."""
    with pytest.raises(InvalidConsentDataError):
        build_otp_challenge(**overrides)
