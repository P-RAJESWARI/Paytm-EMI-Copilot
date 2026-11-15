"""Property-based tests: any valid chain verifies; any one-field edit, removal or reorder is found.

Chains of 1 to 8 records are built from varied synthetic evidence (ids, product names in English
and Tamil, both design plans, phone digits, languages and moments).
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from hypothesis import assume, given
from hypothesis import strategies as st

from emi_copilot.domain.consent import (
    ConsentEvidence,
    ConsentRecord,
    ConsentReference,
    verify_consent_record_chain,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.money import Money
from tests.consent_builders import (
    build_consent_evidence,
    build_consent_idempotency,
    build_plan_snapshot,
)
from tests.sale_builders import build_no_cost_chosen_plan, build_standard_chosen_plan

IDENTIFIER_TEXT = st.text(alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ", min_size=1, max_size=26)
PRODUCT_NAMES = st.text(
    alphabet=st.sampled_from("abcdefgh 0123456789,கைபேசி"), min_size=1, max_size=30
).filter(str.strip)
CONSENT_MOMENTS = st.datetimes(
    min_value=datetime(2026, 1, 1),  # noqa: DTZ001 - hypothesis bounds are naive by design
    max_value=datetime(2027, 12, 31),  # noqa: DTZ001 - hypothesis bounds are naive by design
    timezones=st.just(UTC),
)


@st.composite
def consent_evidence(draw: st.DrawFn) -> ConsentEvidence:
    """Draws valid evidence that varies every field a customer or shop could influence."""
    chosen_plan = draw(st.sampled_from([build_no_cost_chosen_plan(), build_standard_chosen_plan()]))
    return build_consent_evidence(
        consent_id=draw(IDENTIFIER_TEXT),
        sale_id=draw(IDENTIFIER_TEXT),
        customer_session_id=draw(IDENTIFIER_TEXT),
        consent_reference=ConsentReference(f"EMI-2611-{draw(st.integers(0, 9999)):04d}"),
        plan_snapshot=build_plan_snapshot(
            product_name=draw(PRODUCT_NAMES), chosen_plan=chosen_plan
        ),
        phone_last_two_digits=f"{draw(st.integers(0, 99)):02d}",
        language=draw(st.sampled_from(CustomerLanguage)),
        consented_at=draw(CONSENT_MOMENTS),
    )


def build_chain(evidence_list: list[ConsentEvidence]) -> list[ConsentRecord]:
    """Appends each evidence in order, as the repository does under the chain-head lock."""
    records: list[ConsentRecord] = []
    for evidence in evidence_list:
        records.append(
            ConsentRecord.append_after(
                records[-1] if records else None, evidence, build_consent_idempotency()
            )
        )
    return records


CHAINS = st.lists(consent_evidence(), min_size=1, max_size=8).map(build_chain)


def _flip_last_hex_digit(hex_digest: str) -> str:
    """Gives another valid digest that differs only in its last character."""
    return hex_digest[:-1] + ("0" if hex_digest[-1] != "0" else "1")


def _with_evidence(record: ConsentRecord, **changes: object) -> ConsentRecord:
    """Gives the record with some evidence fields changed and its stored hashes untouched."""
    return replace(record, evidence=replace(record.evidence, **changes))  # type: ignore[arg-type]


def _with_plan(record: ConsentRecord, **changes: object) -> ConsentRecord:
    """Gives the record with some chosen plan fields changed and its stored hashes untouched."""
    plan_snapshot = record.evidence.plan_snapshot
    chosen_plan = replace(plan_snapshot.chosen_plan, **changes)  # type: ignore[arg-type]
    return _with_evidence(record, plan_snapshot=replace(plan_snapshot, chosen_plan=chosen_plan))


def _other_reference(record: ConsentRecord) -> ConsentReference:
    """Gives a reference with the next serial number."""
    serial_number = int(record.evidence.consent_reference.value[-4:])
    return ConsentReference(f"EMI-2611-{(serial_number + 1) % 10_000:04d}")


ONE_FIELD_TAMPERS: dict[str, Callable[[ConsentRecord], ConsentRecord]] = {
    "consent_id": lambda record: _with_evidence(record, consent_id=record.id + "X"),
    "sale_id": lambda record: _with_evidence(record, sale_id=record.evidence.sale_id + "X"),
    "customer_session_id": lambda record: _with_evidence(
        record, customer_session_id=record.evidence.customer_session_id + "X"
    ),
    "consent_reference": lambda record: _with_evidence(
        record, consent_reference=_other_reference(record)
    ),
    "product_id": lambda record: _with_evidence(
        record,
        plan_snapshot=replace(
            record.evidence.plan_snapshot,
            product_id=record.evidence.plan_snapshot.product_id + "X",
        ),
    ),
    "product_name": lambda record: _with_evidence(
        record,
        plan_snapshot=replace(
            record.evidence.plan_snapshot,
            product_name=record.evidence.plan_snapshot.product_name + "X",
        ),
    ),
    "monthly_installment": lambda record: _with_plan(
        record,
        monthly_installment=record.evidence.plan_snapshot.chosen_plan.monthly_installment
        + Money.from_paise(1),
    ),
    "tenure_in_months": lambda record: _with_plan(
        record,
        tenure_in_months=record.evidence.plan_snapshot.chosen_plan.tenure_in_months + 1,
    ),
    "lender_label": lambda record: _with_plan(
        record, lender_label=record.evidence.plan_snapshot.chosen_plan.lender_label + "X"
    ),
    "phone_last_two_digits": lambda record: _with_evidence(
        record,
        phone_last_two_digits=f"{(int(record.evidence.phone_last_two_digits) + 1) % 100:02d}",
    ),
    "phone_hash": lambda record: _with_evidence(
        record, phone_hash=_flip_last_hex_digit(record.evidence.phone_hash)
    ),
    "language": lambda record: _with_evidence(
        record,
        language=(
            CustomerLanguage.TAMIL
            if record.evidence.language is CustomerLanguage.ENGLISH
            else CustomerLanguage.ENGLISH
        ),
    ),
    "cooling_off_wording_version": lambda record: _with_evidence(
        record, cooling_off_wording_version=record.evidence.cooling_off_wording_version + "X"
    ),
    "consented_at": lambda record: _with_evidence(
        record, consented_at=record.evidence.consented_at + timedelta(microseconds=1)
    ),
    "record_hash": lambda record: replace(
        record, record_hash=_flip_last_hex_digit(record.record_hash)
    ),
}
# Changing the position or the link of the first record breaks its shape, so the record cannot
# even be built; these two apply from the second record on.
LATER_RECORD_TAMPERS: dict[str, Callable[[ConsentRecord], ConsentRecord]] = {
    "chain_position": lambda record: replace(record, chain_position=record.chain_position + 1),
    "previous_record_hash": lambda record: replace(
        record, previous_record_hash=_flip_last_hex_digit(record.previous_record_hash)
    ),
}


@given(records=CHAINS)
def test_a_chain_of_valid_appends_verifies(records: list[ConsentRecord]) -> None:
    """Every chain built by append_after is intact, whatever the evidence."""
    verification = verify_consent_record_chain(records)
    assert verification.is_intact
    assert verification.checked_record_count == len(records)


@given(records=CHAINS)
def test_sealing_the_same_evidence_again_gives_the_same_hashes(
    records: list[ConsentRecord],
) -> None:
    """Hashing is deterministic, so a stored chain can be re-checked at any time."""
    rebuilt_records = build_chain([record.evidence for record in records])
    assert [record.record_hash for record in rebuilt_records] == [
        record.record_hash for record in records
    ]


@given(records=CHAINS, data=st.data())
def test_any_single_field_tamper_is_found_at_the_tampered_record(
    records: list[ConsentRecord], data: st.DataObject
) -> None:
    """Changing one stored field of one record breaks the chain exactly there."""
    tampered_index = data.draw(st.integers(0, len(records) - 1))
    available_tampers = dict(ONE_FIELD_TAMPERS)
    if tampered_index > 0:
        available_tampers.update(LATER_RECORD_TAMPERS)
    tamper_name = data.draw(st.sampled_from(sorted(available_tampers)))
    tampered_records = list(records)
    tampered_records[tampered_index] = available_tampers[tamper_name](records[tampered_index])
    verification = verify_consent_record_chain(tampered_records)
    assert verification.first_broken_index == tampered_index


@given(records=CHAINS, data=st.data())
def test_any_reordering_is_found_at_the_first_moved_record(
    records: list[ConsentRecord], data: st.DataObject
) -> None:
    """Swapping or shuffling stored records breaks the chain at the first moved position."""
    assume(len(records) >= 2)
    new_order = data.draw(st.permutations(range(len(records))))
    assume(new_order != list(range(len(records))))
    first_moved_index = next(
        index for index, original_index in enumerate(new_order) if index != original_index
    )
    verification = verify_consent_record_chain([records[index] for index in new_order])
    assert verification.first_broken_index == first_moved_index


@given(records=CHAINS, data=st.data())
def test_removing_any_record_but_the_last_is_found_where_it_was(
    records: list[ConsentRecord], data: st.DataObject
) -> None:
    """A gap in the chain is found at the record after it."""
    assume(len(records) >= 2)
    removed_index = data.draw(st.integers(0, len(records) - 2))
    remaining_records = records[:removed_index] + records[removed_index + 1 :]
    assert verify_consent_record_chain(remaining_records).first_broken_index == removed_index
