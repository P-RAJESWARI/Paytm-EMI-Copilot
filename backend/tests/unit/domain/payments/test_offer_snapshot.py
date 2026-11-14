"""Tests for the OfferSnapshot value object and its JSON-compatible dictionary form."""

import json
from dataclasses import replace
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.domain.errors import InvalidOfferSnapshotError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType, OfferSnapshot
from tests.payment_builders import build_no_cost_offer_snapshot, build_standard_offer_snapshot

CARD_FIELD_WORDS = ("card", "cvv", "expiry", "bin")


@st.composite
def valid_offer_snapshots(draw: st.DrawFn) -> OfferSnapshot:
    """Draws a self-consistent snapshot: installments sum to the total and the price is positive."""
    tenure_in_months = draw(st.integers(min_value=1, max_value=60))
    regular_installment_in_paise = draw(st.integers(min_value=1, max_value=10**12))
    last_installment_in_paise = (
        regular_installment_in_paise
        if tenure_in_months == 1
        else draw(st.integers(min_value=0, max_value=10**12))
    )
    total_payable_in_paise = (
        regular_installment_in_paise * (tenure_in_months - 1) + last_installment_in_paise
    )
    emi_type = draw(st.sampled_from(EmiType))
    extra_in_total_in_paise = (
        0
        if emi_type is EmiType.NO_COST
        else draw(st.integers(min_value=0, max_value=total_payable_in_paise - 1))
    )
    return OfferSnapshot(
        offer_id=draw(st.text(min_size=1, max_size=40).filter(str.strip)),
        lender_label=draw(st.text(min_size=1, max_size=40).filter(str.strip)),
        emi_type=emi_type,
        tenure_in_months=tenure_in_months,
        regular_installment=Money.from_paise(regular_installment_in_paise),
        last_installment=Money.from_paise(last_installment_in_paise),
        total_payable=Money.from_paise(total_payable_in_paise),
        extra_in_total=Money.from_paise(extra_in_total_in_paise),
    )


@given(valid_offer_snapshots())
def test_offer_snapshot_dictionary_round_trip_returns_equal_snapshot(
    offer_snapshot: OfferSnapshot,
) -> None:
    """Encoding to a dictionary, through JSON text, and decoding gives back the same snapshot."""
    stored_json_text = json.dumps(offer_snapshot.to_dictionary())
    assert OfferSnapshot.from_dictionary(json.loads(stored_json_text)) == offer_snapshot


def test_offer_snapshot_to_dictionary_stores_integer_paise_and_enum_value() -> None:
    """The stored form holds integer paise and our own EMI type words, never floats."""
    assert build_no_cost_offer_snapshot().to_dictionary() == {
        "offer_id": "offer-plan-a",
        "lender_label": "Brand",
        "emi_type": "NO_COST",
        "tenure_in_months": 6,
        "regular_installment_in_paise": 366_667,
        "last_installment_in_paise": 366_665,
        "total_payable_in_paise": 2_200_000,
        "extra_in_total_in_paise": 0,
    }


def test_offer_snapshot_dictionary_has_no_card_fields() -> None:
    """No card data is ever part of the stored plan (CLAUDE.md rule 3)."""
    for key in build_standard_offer_snapshot().to_dictionary():
        assert not any(card_word in key for card_word in CARD_FIELD_WORDS)


def test_offer_snapshot_is_immutable() -> None:
    """A frozen snapshot cannot be changed after the customer has seen it."""
    offer_snapshot = build_standard_offer_snapshot()
    with pytest.raises(AttributeError):
        offer_snapshot.tenure_in_months = 12  # type: ignore[misc]


def test_offer_snapshot_with_one_month_single_installment_is_valid() -> None:
    """A one-month plan is valid when its single installment is the whole total."""
    offer_snapshot = replace(
        build_standard_offer_snapshot(),
        tenure_in_months=1,
        regular_installment=Money.from_rupees("23100"),
        last_installment=Money.from_rupees("23100"),
    )
    assert offer_snapshot.total_payable == Money.from_rupees("23100")


@pytest.mark.parametrize(
    ("field_overrides", "expected_message"),
    [
        ({"offer_id": " "}, "offer id"),
        ({"offer_id": 7}, "offer id"),
        ({"lender_label": ""}, "lender label"),
        ({"emi_type": "NO_COST"}, "EmiType"),
        ({"tenure_in_months": 0}, "at least 1 month"),
        ({"tenure_in_months": True}, "whole number"),
        ({"tenure_in_months": "6"}, "whole number"),
        ({"regular_installment": Money.from_rupees("3850.001")}, "regular installment"),
        ({"last_installment": Decimal("3850.00")}, "last installment"),
        ({"total_payable": Money.from_rupees("23100.50")}, "add up"),
        ({"extra_in_total": Money.from_rupees("23100")}, "below the total payable"),
        ({"emi_type": EmiType.NO_COST}, "no-cost plan has no extra"),
    ],
)
def test_offer_snapshot_with_invalid_field_raises_invalid_offer_snapshot_error(
    field_overrides: dict[str, object], expected_message: str
) -> None:
    """Every inconsistent or mistyped field is rejected on creation with a typed error."""
    with pytest.raises(InvalidOfferSnapshotError, match=expected_message):
        replace(build_standard_offer_snapshot(), **field_overrides)  # type: ignore[arg-type]


def test_offer_snapshot_one_month_with_two_different_installments_raises() -> None:
    """A one-month plan cannot show a regular installment that differs from its only one."""
    with pytest.raises(InvalidOfferSnapshotError, match="single installment"):
        replace(
            build_standard_offer_snapshot(),
            tenure_in_months=1,
            regular_installment=Money.from_rupees("100"),
            last_installment=Money.from_rupees("23100"),
        )


@pytest.mark.parametrize(
    ("key", "stored_value", "expected_message"),
    [
        ("offer_id", 17, "must be text"),
        ("emi_type", "SUBVENTION", "not a known EmiType"),
        ("tenure_in_months", "6", "must be an integer"),
        ("tenure_in_months", True, "must be an integer"),
        ("total_payable_in_paise", 2_310_000.0, "must be an integer"),
        ("extra_in_total_in_paise", -1, "cannot be negative"),
    ],
)
def test_offer_snapshot_from_dictionary_with_bad_value_raises_invalid_offer_snapshot_error(
    key: str, stored_value: object, expected_message: str
) -> None:
    """A stored value of the wrong type or range is rejected instead of being coerced."""
    stored_dictionary: dict[str, object] = dict(build_standard_offer_snapshot().to_dictionary())
    stored_dictionary[key] = stored_value
    with pytest.raises(InvalidOfferSnapshotError, match=expected_message):
        OfferSnapshot.from_dictionary(stored_dictionary)


@pytest.mark.parametrize("change", ["missing key", "extra key"])
def test_offer_snapshot_from_dictionary_with_wrong_keys_raises_invalid_offer_snapshot_error(
    change: str,
) -> None:
    """A stored snapshot with a missing or unexpected key is rejected, never partly read."""
    stored_dictionary: dict[str, object] = dict(build_standard_offer_snapshot().to_dictionary())
    if change == "missing key":
        del stored_dictionary["lender_label"]
    else:
        stored_dictionary["card_number"] = "never stored"
    with pytest.raises(InvalidOfferSnapshotError, match="exactly the known keys"):
        OfferSnapshot.from_dictionary(stored_dictionary)


def test_emi_type_values_are_stable_stored_words() -> None:
    """EMI types are stored by value, so the values are part of the database contract."""
    assert [emi_type.value for emi_type in EmiType] == ["NO_COST", "STANDARD"]
