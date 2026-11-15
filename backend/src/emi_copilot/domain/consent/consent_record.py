"""ConsentRecord: one append-only, hash-chained consent; written once and never changed."""

from dataclasses import dataclass
from typing import Self

from emi_copilot.domain.consent.consent_evidence import ConsentEvidence
from emi_copilot.domain.consent.consent_record_hasher import ConsentRecordHasher
from emi_copilot.domain.errors import InvalidConsentDataError
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_sha256_hex,
)

GENESIS_PREVIOUS_RECORD_HASH = "0" * 64
"""The previous hash of the first record. A fixed value, not NULL, so the database's unique
previous_record_hash also stops two records from both claiming to be first."""

_CONSENT_RECORD_HASHER = ConsentRecordHasher()


# Pattern: Value Object. Ties a consent to the Idempotency-Key that recorded it (ADR 0005).
@dataclass(frozen=True, slots=True)
class ConsentIdempotency:
    """The Idempotency-Key a consent was recorded with and the SHA-256 of that request.

    Not evidence, so it is not hashed: the fingerprint covers the selection and the figures
    shown, never the one-time code (ADR 0021 decision 5).
    """

    idempotency_key: str
    request_fingerprint: str

    def __post_init__(self) -> None:
        """Rejects a blank key and a malformed fingerprint."""
        require_non_empty_text(self.idempotency_key, "idempotency key", InvalidConsentDataError)
        require_sha256_hex(self.request_fingerprint, "request fingerprint", InvalidConsentDataError)


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    """Consent evidence, its place in the chain, the previous record's hash and its own hash.

    Records form one chain across every sale: record n holds record n - 1's hash, and its own
    hash covers its evidence, position and that link. A record is built with append_after, so
    its hash is right when written; verify_consent_record_chain re-checks stored records.
    """

    evidence: ConsentEvidence
    idempotency: ConsentIdempotency
    chain_position: int
    previous_record_hash: str
    record_hash: str

    def __post_init__(self) -> None:
        """Rejects wrong types, malformed hashes and a first record without the genesis link."""
        if not isinstance(self.evidence, ConsentEvidence):
            raise InvalidConsentDataError("A consent record needs ConsentEvidence.")
        if not isinstance(self.idempotency, ConsentIdempotency):
            raise InvalidConsentDataError("A consent record needs its ConsentIdempotency.")
        if (
            isinstance(self.chain_position, bool)
            or not isinstance(self.chain_position, int)
            or self.chain_position < 1
        ):
            raise InvalidConsentDataError("A chain position is a whole number from 1.")
        require_sha256_hex(
            self.previous_record_hash, "previous record hash", InvalidConsentDataError
        )
        require_sha256_hex(self.record_hash, "record hash", InvalidConsentDataError)
        is_first_record = self.chain_position == 1
        if is_first_record != (self.previous_record_hash == GENESIS_PREVIOUS_RECORD_HASH):
            raise InvalidConsentDataError("Exactly the first record links to the genesis hash.")

    @property
    def id(self) -> str:
        """Gives the consent id."""
        return self.evidence.consent_id

    @classmethod
    def append_after(
        cls,
        previous_record: "ConsentRecord | None",
        evidence: ConsentEvidence,
        idempotency: ConsentIdempotency,
    ) -> Self:
        """Builds the record that follows the chain head (None for the first) with its hash."""
        if previous_record is None:
            chain_position, previous_record_hash = 1, GENESIS_PREVIOUS_RECORD_HASH
        else:
            chain_position = previous_record.chain_position + 1
            previous_record_hash = previous_record.record_hash
        record_hash = _CONSENT_RECORD_HASHER.hash_record_fields(
            evidence, chain_position, previous_record_hash
        )
        return cls(
            evidence=evidence,
            idempotency=idempotency,
            chain_position=chain_position,
            previous_record_hash=previous_record_hash,
            record_hash=record_hash,
        )
