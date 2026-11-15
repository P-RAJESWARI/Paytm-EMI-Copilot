"""ConsentPlanSnapshot round-trips exactly; ConsentEvidence refuses incomplete evidence."""

from datetime import datetime

import pytest

from emi_copilot.domain.consent import ConsentPlanSnapshot
from emi_copilot.domain.errors import InvalidConsentDataError
from emi_copilot.domain.money import Money
from tests.consent_builders import build_consent_evidence, build_plan_snapshot
from tests.sale_builders import PRODUCT_ID


def test_plan_snapshot_stores_paise_and_the_chosen_plan_and_decodes_to_the_same_value() -> None:
    """The stored form is text and integer paise only, and it decodes to an equal snapshot."""
    plan_snapshot = build_plan_snapshot()
    stored_snapshot = plan_snapshot.to_dictionary()
    assert stored_snapshot == {
        "product_id": PRODUCT_ID,
        "product_name": "Example phone, 128 GB",
        "price_in_paise": 2_200_000,
        "chosen_plan": {
            "offer_id": "offer-plan-a",
            "plan_kind": "NO_COST",
            "lender_label": "Brand",
            "tenure_in_months": 6,
            "monthly_installment_in_paise": 366_667,
            "extra_in_total_in_paise": 0,
            "total_payable_in_paise": 2_200_000,
        },
    }
    assert ConsentPlanSnapshot.from_dictionary(stored_snapshot) == plan_snapshot


@pytest.mark.parametrize(
    "overrides",
    [
        {"product_id": ""},
        {"product_name": " "},
        {"chosen_plan": None},
        {"price": Money.from_rupees("21000")},
    ],
    ids=["blank-product", "blank-name", "no-plan", "other-price"],
)
def test_plan_snapshot_refuses_incomplete_or_inconsistent_fields(
    overrides: dict[str, object],
) -> None:
    """The plan must be quoted on exactly the product's price."""
    with pytest.raises(InvalidConsentDataError):
        build_plan_snapshot(**overrides)


def _stored_snapshot_with(**changes: object) -> dict[str, object]:
    """Gives the stored design snapshot with some keys changed or, for the value None, removed."""
    stored_snapshot: dict[str, object] = dict(build_plan_snapshot().to_dictionary())
    for key, value in changes.items():
        if value is None:
            del stored_snapshot[key]
        else:
            stored_snapshot[key] = value
    return stored_snapshot


@pytest.mark.parametrize(
    "stored_snapshot",
    [
        _stored_snapshot_with(product_name=None),
        _stored_snapshot_with(extra_key="value"),
        _stored_snapshot_with(product_id=42),
        _stored_snapshot_with(price_in_paise="2200000"),
        _stored_snapshot_with(price_in_paise=True),
        _stored_snapshot_with(chosen_plan="offer-plan-a"),
        _stored_snapshot_with(chosen_plan={"offer_id": "offer-plan-a"}),
    ],
    ids=[
        "missing-key",
        "extra-key",
        "number-as-text-field",
        "price-as-text",
        "price-as-bool",
        "plan-as-text",
        "incomplete-plan",
    ],
)
def test_plan_snapshot_from_dictionary_refuses_malformed_stored_values(
    stored_snapshot: dict[str, object],
) -> None:
    """A stored snapshot is decoded exactly or not at all, always as a consent data error."""
    with pytest.raises(InvalidConsentDataError):
        ConsentPlanSnapshot.from_dictionary(stored_snapshot)


@pytest.mark.parametrize(
    "overrides",
    [
        {"consent_id": ""},
        {"sale_id": " "},
        {"customer_session_id": ""},
        {"cooling_off_wording_version": ""},
        {"consent_reference": "EMI-2611-0042"},
        {"plan_snapshot": None},
        {"language": "en"},
        {"phone_last_two_digits": "042"},
        {"phone_last_two_digits": 42},
        {"phone_hash": "9000000042"},
        {"consented_at": datetime(2026, 11, 26, 9, 38)},  # noqa: DTZ001 - a naive moment on purpose
    ],
    ids=[
        "blank-consent-id",
        "blank-sale",
        "blank-session",
        "blank-wording-version",
        "reference-as-text",
        "no-snapshot",
        "language-as-text",
        "three-digits",
        "digits-as-integer",
        "plain-number-instead-of-hash",
        "naive-moment",
    ],
)
def test_consent_evidence_refuses_incomplete_or_personal_fields(
    overrides: dict[str, object],
) -> None:
    """Only the last two digits and a hash of the phone may be kept."""
    with pytest.raises(InvalidConsentDataError):
        build_consent_evidence(**overrides)
