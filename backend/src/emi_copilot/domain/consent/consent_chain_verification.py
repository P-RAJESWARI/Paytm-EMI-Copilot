"""Checks a run of stored consent records for edits, removals and reordering."""

from collections.abc import Sequence
from dataclasses import dataclass

from emi_copilot.domain.consent.consent_record import GENESIS_PREVIOUS_RECORD_HASH, ConsentRecord
from emi_copilot.domain.consent.consent_record_hasher import ConsentRecordHasher


@dataclass(frozen=True, slots=True)
class ConsentChainVerification:
    """The result of a chain check: how many records were checked and the first broken one.

    first_broken_index is the 0-based index in the checked sequence, or None when every
    record's hash, position and link are right.
    """

    checked_record_count: int
    first_broken_index: int | None

    @property
    def is_intact(self) -> bool:
        """Tells whether no record was found broken."""
        return self.first_broken_index is None


def _is_record_intact(
    record: ConsentRecord, expected_position: int, expected_previous_hash: str
) -> bool:
    """Tells whether a record sits where expected, links back correctly and hashes to itself."""
    recomputed_hash = ConsentRecordHasher().hash_record_fields(
        record.evidence, record.chain_position, record.previous_record_hash
    )
    return (
        record.chain_position == expected_position
        and record.previous_record_hash == expected_previous_hash
        and record.record_hash == recomputed_hash
    )


def verify_consent_record_chain(records: Sequence[ConsentRecord]) -> ConsentChainVerification:
    """Checks a whole chain, from the first record, in chain order.

    Any change to a field, a removed or inserted record, or a swapped order breaks it at the
    first affected index. Removing records from the end cannot be seen from the records alone;
    the database's append-only trigger guards against that.
    """
    expected_previous_hash = GENESIS_PREVIOUS_RECORD_HASH
    for index, record in enumerate(records):
        if not _is_record_intact(record, index + 1, expected_previous_hash):
            return ConsentChainVerification(len(records), index)
        expected_previous_hash = record.record_hash
    return ConsentChainVerification(len(records), None)
