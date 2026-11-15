"""ConsentRecord: sealing, the canonical form (known answer) and chain verification examples."""

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest

from emi_copilot.domain.consent import (
    GENESIS_PREVIOUS_RECORD_HASH,
    ConsentIdempotency,
    ConsentRecord,
    ConsentRecordHasher,
    verify_consent_record_chain,
)
from emi_copilot.domain.consent.consent_record_hasher import format_canonical_moment
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import InvalidConsentDataError
from tests.consent_builders import (
    CONSENT_ID,
    CONSENTED_AT,
    build_consent_evidence,
    build_consent_idempotency,
    build_first_consent_record,
    build_plan_snapshot,
)

DESIGN_CANONICAL_TEXT = (
    '{"canonical_form_version":1,"chain_position":1,"consent_id":"01JCCONSENT000000000000001",'
    '"consent_reference":"EMI-2611-0042","consented_at":"2026-11-26T09:38:00.000000Z",'
    '"cooling_off_wording_version":"cooling-off-placeholder-v1",'
    '"customer_session_id":"01JCSESSION000000000000001","language":"en",'
    '"phone_hash":"' + "c" * 64 + '","phone_last_two_digits":"42",'
    '"plan_snapshot":{"chosen_plan":{"extra_in_total_in_paise":0,"lender_label":"Brand",'
    '"monthly_installment_in_paise":366667,"offer_id":"offer-plan-a","plan_kind":"NO_COST",'
    '"tenure_in_months":6,"total_payable_in_paise":2200000},"price_in_paise":2200000,'
    '"product_id":"01JCPRODUCT000000000000001","product_name":"Example phone, 128 GB"},'
    '"previous_record_hash":"' + "0" * 64 + '","sale_id":"01JCSALE000000000000000001"}'
)
# A SHA-256 known answer, not a secret.
# pragma: allowlist nextline secret
DESIGN_RECORD_HASH = "4804e690fabfe1a789f7b4000f7ec855d4be5f19083b0c96d6f35342241111a7"


def build_second_record(first_record: ConsentRecord) -> ConsentRecord:
    """A second consent, a minute later on another sale, appended after first_record."""
    return ConsentRecord.append_after(
        first_record,
        build_consent_evidence(
            consent_id="01JCCONSENT000000000000002",
            sale_id="01JCSALE000000000000000002",
            consented_at=CONSENTED_AT + timedelta(minutes=1),
        ),
        build_consent_idempotency("consent-key-0002"),
    )


def test_canonical_bytes_are_sorted_compact_json_with_paise_and_utc_moments() -> None:
    """Known answer: the design consent hashes these exact bytes to this exact digest."""
    first_record = build_first_consent_record()
    canonical_bytes = ConsentRecordHasher().build_canonical_bytes(
        first_record.evidence, 1, GENESIS_PREVIOUS_RECORD_HASH
    )
    assert canonical_bytes.decode("ascii") == DESIGN_CANONICAL_TEXT
    assert hashlib.sha256(canonical_bytes).hexdigest() == DESIGN_RECORD_HASH
    assert first_record.record_hash == DESIGN_RECORD_HASH


def test_canonical_moment_is_the_same_instant_in_utc_whatever_the_offset() -> None:
    """An IST moment and its UTC equal hash alike."""
    india_standard_time = timezone(timedelta(hours=5, minutes=30))
    moment_in_india = datetime(2026, 11, 26, 15, 8, tzinfo=india_standard_time)
    assert format_canonical_moment(moment_in_india) == "2026-11-26T09:38:00.000000Z"
    assert format_canonical_moment(moment_in_india.astimezone(UTC)) == (
        "2026-11-26T09:38:00.000000Z"
    )


def test_canonical_bytes_escape_tamil_text_as_ascii() -> None:
    """A Tamil product name hashes through stable ASCII escapes, never raw UTF-8."""
    evidence = build_consent_evidence(
        language=CustomerLanguage.TAMIL,
        plan_snapshot=build_plan_snapshot(product_name="கைபேசி"),
    )
    canonical_bytes = ConsentRecordHasher().build_canonical_bytes(
        evidence, 1, GENESIS_PREVIOUS_RECORD_HASH
    )
    assert canonical_bytes.isascii()
    assert b'"product_name":"\\u0b95' in canonical_bytes
    assert b'"language":"ta"' in canonical_bytes


def test_append_after_none_starts_the_chain_at_position_one_from_genesis() -> None:
    """The first record links to the fixed genesis hash."""
    first_record = build_first_consent_record()
    assert first_record.id == CONSENT_ID
    assert first_record.chain_position == 1
    assert first_record.previous_record_hash == GENESIS_PREVIOUS_RECORD_HASH
    assert first_record.idempotency == build_consent_idempotency()


def test_append_after_links_to_the_previous_record_and_the_chain_verifies() -> None:
    """Record 2 holds record 1's hash, and the two verify as an intact chain."""
    first_record = build_first_consent_record()
    second_record = build_second_record(first_record)
    assert second_record.chain_position == 2
    assert second_record.previous_record_hash == first_record.record_hash
    verification = verify_consent_record_chain([first_record, second_record])
    assert verification.is_intact
    assert verification.checked_record_count == 2
    assert verification.first_broken_index is None


def test_an_empty_chain_is_intact() -> None:
    """No records means nothing to break."""
    assert verify_consent_record_chain([]).is_intact


def test_verify_finds_an_edited_field_at_its_index() -> None:
    """Changing a stored field after the fact is detected at that record."""
    first_record = build_first_consent_record()
    second_record = build_second_record(first_record)
    edited_evidence = replace(second_record.evidence, phone_last_two_digits="43")
    verification = verify_consent_record_chain(
        [first_record, replace(second_record, evidence=edited_evidence)]
    )
    assert not verification.is_intact
    assert verification.first_broken_index == 1


def test_verify_finds_a_chain_that_does_not_start_from_genesis() -> None:
    """Dropping the first record breaks the chain at index 0."""
    first_record = build_first_consent_record()
    verification = verify_consent_record_chain([build_second_record(first_record)])
    assert verification.first_broken_index == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"evidence": None},
        {"idempotency": None},
        {"chain_position": 0},
        {"chain_position": True},
        {"previous_record_hash": "x" * 64},
        {"record_hash": ""},
        {"chain_position": 2},
    ],
    ids=[
        "no-evidence",
        "no-idempotency",
        "position-zero",
        "position-bool",
        "bad-previous-hash",
        "bad-record-hash",
        "second-position-with-genesis-link",
    ],
)
def test_consent_record_refuses_malformed_fields(overrides: dict[str, object]) -> None:
    """A record cannot be built with a broken shape, so a repository can never load one."""
    with pytest.raises(InvalidConsentDataError):
        replace(build_first_consent_record(), **overrides)  # type: ignore[arg-type]


def test_consent_record_refuses_a_first_position_without_the_genesis_link() -> None:
    """Only the first record links to genesis, and the first must."""
    with pytest.raises(InvalidConsentDataError):
        replace(build_first_consent_record(), previous_record_hash="f" * 64)


@pytest.mark.parametrize(
    ("idempotency_key", "request_fingerprint"),
    [(" ", "d" * 64), ("consent-key-0001", "not-a-digest")],
    ids=["blank-key", "bad-fingerprint"],
)
def test_consent_idempotency_refuses_a_blank_key_or_bad_fingerprint(
    idempotency_key: str, request_fingerprint: str
) -> None:
    """The key and the fingerprint are both needed to replay a consent."""
    with pytest.raises(InvalidConsentDataError):
        ConsentIdempotency(idempotency_key, request_fingerprint)
