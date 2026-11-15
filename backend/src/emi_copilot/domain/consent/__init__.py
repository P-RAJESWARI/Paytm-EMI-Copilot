"""Consent types: the phone number, the one-time code challenge and hash-chained consent records."""

from emi_copilot.domain.consent.consent_chain_verification import (
    ConsentChainVerification,
    verify_consent_record_chain,
)
from emi_copilot.domain.consent.consent_evidence import ConsentEvidence
from emi_copilot.domain.consent.consent_plan_snapshot import (
    ConsentPlanSnapshot,
    ConsentPlanSnapshotDictionary,
)
from emi_copilot.domain.consent.consent_record import (
    GENESIS_PREVIOUS_RECORD_HASH,
    ConsentIdempotency,
    ConsentRecord,
)
from emi_copilot.domain.consent.consent_record_hasher import (
    CANONICAL_FORM_VERSION,
    ConsentRecordHasher,
)
from emi_copilot.domain.consent.consent_reference import ConsentReference
from emi_copilot.domain.consent.customer_phone_number import CustomerPhoneNumber
from emi_copilot.domain.consent.otp_challenge import (
    OtpChallenge,
    OtpVerificationAttempt,
    OtpVerificationOutcome,
)

__all__ = [
    "CANONICAL_FORM_VERSION",
    "GENESIS_PREVIOUS_RECORD_HASH",
    "ConsentChainVerification",
    "ConsentEvidence",
    "ConsentIdempotency",
    "ConsentPlanSnapshot",
    "ConsentPlanSnapshotDictionary",
    "ConsentRecord",
    "ConsentRecordHasher",
    "ConsentReference",
    "CustomerPhoneNumber",
    "OtpChallenge",
    "OtpVerificationAttempt",
    "OtpVerificationOutcome",
    "verify_consent_record_chain",
]
