"""ConsentRecordHasher: SHA-256 over a canonical JSON form of a consent record's evidence."""

import hashlib
import json
from datetime import UTC, datetime

from emi_copilot.domain.consent.consent_evidence import ConsentEvidence

CANONICAL_FORM_VERSION = 1
"""Hashed with every record, so a later change of the canonical form is told apart from tamper."""


def format_canonical_moment(moment: datetime) -> str:
    """Writes a moment in UTC as ISO 8601 with microseconds and a Z, the database's precision."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _build_canonical_payload(
    evidence: ConsentEvidence, chain_position: int, previous_record_hash: str
) -> dict[str, object]:
    """Gives every evidential field and chain link as JSON text, integers and objects; no floats."""
    return {
        "canonical_form_version": CANONICAL_FORM_VERSION,
        "chain_position": chain_position,
        "previous_record_hash": previous_record_hash,
        "consent_id": evidence.consent_id,
        "sale_id": evidence.sale_id,
        "customer_session_id": evidence.customer_session_id,
        "consent_reference": evidence.consent_reference.value,
        "plan_snapshot": evidence.plan_snapshot.to_dictionary(),
        "phone_last_two_digits": evidence.phone_last_two_digits,
        "phone_hash": evidence.phone_hash,
        "language": evidence.language.value,
        "cooling_off_wording_version": evidence.cooling_off_wording_version,
        "consented_at": format_canonical_moment(evidence.consented_at),
    }


class ConsentRecordHasher:
    """Hashes a record's evidence with its chain position and the previous record's hash.

    The canonical form is JSON with sorted keys, no spaces and ASCII escapes, so the same
    evidence always gives the same bytes. Money is integer paise and moments are UTC with a Z.
    Linking each record to the previous record's hash makes any edit, removal or reordering
    detectable by verify_consent_record_chain (security-and-compliance.md section 9).
    """

    def build_canonical_bytes(
        self, evidence: ConsentEvidence, chain_position: int, previous_record_hash: str
    ) -> bytes:
        """Gives the exact bytes that are hashed for one record."""
        payload = _build_canonical_payload(evidence, chain_position, previous_record_hash)
        canonical_text = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return canonical_text.encode("ascii")

    def hash_record_fields(
        self, evidence: ConsentEvidence, chain_position: int, previous_record_hash: str
    ) -> str:
        """Gives the lowercase hex SHA-256 of the canonical bytes: the record's hash."""
        canonical_bytes = self.build_canonical_bytes(evidence, chain_position, previous_record_hash)
        return hashlib.sha256(canonical_bytes).hexdigest()
