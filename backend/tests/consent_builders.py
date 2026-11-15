"""Builders of valid customer sessions, OTP challenges and consent records with synthetic values."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from emi_copilot.domain.consent import (
    ConsentEvidence,
    ConsentIdempotency,
    ConsentPlanSnapshot,
    ConsentRecord,
    ConsentReference,
    OtpChallenge,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage, CustomerSession
from emi_copilot.domain.money import Money
from tests.sale_builders import PRODUCT_ID, SALE_ID, build_no_cost_chosen_plan

SESSION_STARTED_AT = datetime(2026, 11, 26, 9, 30, tzinfo=UTC)
CUSTOMER_SESSION_ID = "01JCSESSION000000000000001"
SESSION_LIFETIME = timedelta(minutes=30)
SYNTHETIC_SESSION_TOKEN_HASH = "a" * 64
OTP_CHALLENGE_ID = "01JCOTP0000000000000000001"
SYNTHETIC_OTP_CODE_HASH = "b" * 64
OTP_LIFETIME = timedelta(minutes=5)
OTP_RESEND_WAIT = timedelta(seconds=30)
OTP_MAXIMUM_ATTEMPTS = 3
CONSENT_ID = "01JCCONSENT000000000000001"
SYNTHETIC_PHONE_HASH = "c" * 64
CONSENTED_AT = SESSION_STARTED_AT + timedelta(minutes=8)
PLACEHOLDER_COOLING_OFF_WORDING_VERSION = "cooling-off-placeholder-v1"
SYNTHETIC_REQUEST_FINGERPRINT = "d" * 64


def build_customer_session(**overrides: object) -> CustomerSession:
    """A 30-minute session on SALE_ID started at SESSION_STARTED_AT, nothing chosen yet."""
    customer_session = CustomerSession.start(
        customer_session_id=CUSTOMER_SESSION_ID,
        sale_id=SALE_ID,
        token_hash=SYNTHETIC_SESSION_TOKEN_HASH,
        started_at=SESSION_STARTED_AT,
        lifetime=SESSION_LIFETIME,
    )
    return replace(customer_session, **overrides)  # type: ignore[arg-type]


def build_otp_challenge(**overrides: object) -> OtpChallenge:
    """A fresh 3-attempt challenge for CUSTOMER_SESSION_ID issued at SESSION_STARTED_AT."""
    otp_challenge = OtpChallenge.issue(
        challenge_id=OTP_CHALLENGE_ID,
        customer_session_id=CUSTOMER_SESSION_ID,
        code_hash=SYNTHETIC_OTP_CODE_HASH,
        issued_at=SESSION_STARTED_AT,
        lifetime=OTP_LIFETIME,
        resend_wait=OTP_RESEND_WAIT,
        maximum_attempts=OTP_MAXIMUM_ATTEMPTS,
    )
    return replace(otp_challenge, **overrides)  # type: ignore[arg-type]


def build_plan_snapshot(**overrides: object) -> ConsentPlanSnapshot:
    """Design plan A on the ₹22,000 128 GB phone, as shown on C9."""
    plan_snapshot = ConsentPlanSnapshot(
        product_id=PRODUCT_ID,
        product_name="Example phone, 128 GB",
        price=Money.from_rupees("22000"),
        chosen_plan=build_no_cost_chosen_plan(),
    )
    return replace(plan_snapshot, **overrides)  # type: ignore[arg-type]


def build_consent_evidence(**overrides: object) -> ConsentEvidence:
    """The design receipt's consent: plan A, phone ending 42, English, EMI-2611-0042."""
    consent_evidence = ConsentEvidence(
        consent_id=CONSENT_ID,
        sale_id=SALE_ID,
        customer_session_id=CUSTOMER_SESSION_ID,
        consent_reference=ConsentReference("EMI-2611-0042"),
        plan_snapshot=build_plan_snapshot(),
        phone_last_two_digits="42",
        phone_hash=SYNTHETIC_PHONE_HASH,
        language=CustomerLanguage.ENGLISH,
        cooling_off_wording_version=PLACEHOLDER_COOLING_OFF_WORDING_VERSION,
        consented_at=CONSENTED_AT,
    )
    return replace(consent_evidence, **overrides)  # type: ignore[arg-type]


def build_consent_idempotency(idempotency_key: str = "consent-key-0001") -> ConsentIdempotency:
    """An Idempotency-Key with a synthetic request fingerprint."""
    return ConsentIdempotency(idempotency_key, SYNTHETIC_REQUEST_FINGERPRINT)


def build_first_consent_record(**evidence_overrides: object) -> ConsentRecord:
    """The first record of a chain, sealed over the design evidence."""
    return ConsentRecord.append_after(
        None, build_consent_evidence(**evidence_overrides), build_consent_idempotency()
    )
