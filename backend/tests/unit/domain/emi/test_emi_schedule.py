"""Tests for the EmiSchedule value object and the shared even-split rule."""

import dataclasses
from typing import Any, cast

import pytest

from emi_copilot.domain.emi import EmiSchedule, require_valid_emi_terms, split_total_payable_evenly
from emi_copilot.domain.errors import EmiScheduleNotRepresentableError, InvalidEmiTermsError
from emi_copilot.domain.money import Money

PLAN_A_PRINCIPAL = Money.from_rupees("22000")


def build_schedule(**overrides: object) -> EmiSchedule:
    """Builds design plan A directly, with any field replaced by an override."""
    fields: dict[str, Any] = {
        "principal": PLAN_A_PRINCIPAL,
        "tenure_in_months": 6,
        "regular_installment": Money.from_rupees("3666.67"),
        "last_installment": Money.from_rupees("3666.65"),
    }
    fields.update(overrides)
    return EmiSchedule(**fields)


def test_emi_schedule_valid_fields_derive_installments_total_and_extra() -> None:
    """Installments, total and extra all follow exactly from the stored amounts."""
    schedule = build_schedule(last_installment=Money.from_rupees("3700"))

    assert schedule.installments == (Money.from_rupees("3666.67"),) * 5 + (
        Money.from_rupees("3700"),
    )
    assert schedule.total_payable == Money.from_rupees("22033.35")
    assert schedule.extra_in_total == Money.from_rupees("33.35")


def test_emi_schedule_one_month_has_single_installment_equal_to_total() -> None:
    """A one-month plan has one installment that is both regular and last."""
    schedule = build_schedule(
        tenure_in_months=1,
        regular_installment=PLAN_A_PRINCIPAL,
        last_installment=PLAN_A_PRINCIPAL,
    )

    assert schedule.installments == (PLAN_A_PRINCIPAL,)
    assert schedule.total_payable == PLAN_A_PRINCIPAL


def test_emi_schedule_assignment_raises_because_it_is_immutable() -> None:
    """A schedule cannot be changed after creation."""
    schedule = build_schedule()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cast(Any, schedule).last_installment = Money.from_rupees("1")


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"principal": 22000},
        {"principal": Money.from_rupees("22000.005")},
        {"principal": Money.from_paise(0)},
        {"tenure_in_months": 0},
        {"tenure_in_months": -6},
        {"tenure_in_months": True},
        {"tenure_in_months": 6.0},
        {"regular_installment": Money.from_rupees("3666.666")},
        {"last_installment": "3666.65"},
        {"tenure_in_months": 1, "last_installment": PLAN_A_PRINCIPAL},
        {"last_installment": Money.from_rupees("3666.64")},
    ],
    ids=[
        "principal not money",
        "principal sub-paise",
        "principal zero",
        "tenure zero",
        "tenure negative",
        "tenure bool",
        "tenure float",
        "regular sub-paise",
        "last not money",
        "one month with two amounts",
        "total below principal",
    ],
)
def test_emi_schedule_invalid_fields_raise_invalid_emi_terms_error(
    invalid_fields: dict[str, object],
) -> None:
    """A schedule with invalid terms or inconsistent amounts can never be created."""
    with pytest.raises(InvalidEmiTermsError):
        build_schedule(**invalid_fields)


def test_require_valid_emi_terms_valid_terms_returns_without_error() -> None:
    """Positive whole-paise principal and a tenure of at least one month are accepted."""
    require_valid_emi_terms(Money.from_paise(1), 1)


def test_split_total_payable_evenly_remainder_goes_on_last_installment() -> None:
    """The total is split half-up into equal installments and the last takes the remainder."""
    schedule = split_total_payable_evenly(PLAN_A_PRINCIPAL, 6, PLAN_A_PRINCIPAL)

    assert schedule.regular_installment == Money.from_rupees("3666.67")
    assert schedule.last_installment == Money.from_rupees("3666.65")
    assert schedule.total_payable == PLAN_A_PRINCIPAL


def test_split_total_payable_evenly_rounded_regulars_exceed_total_raises_not_representable() -> (
    None
):
    """₹0.30 over 60 months rounds to ₹0.01 each, and 59 of those already exceed ₹0.30."""
    tiny_total = Money.from_rupees("0.30")
    with pytest.raises(EmiScheduleNotRepresentableError) as raised_error:
        split_total_payable_evenly(tiny_total, 60, tiny_total)
    assert raised_error.value.code == "EMI_SCHEDULE_NOT_REPRESENTABLE"


def test_split_total_payable_evenly_sub_paise_total_raises_invalid_emi_terms_error() -> None:
    """The total to split must already be whole paise."""
    with pytest.raises(InvalidEmiTermsError):
        split_total_payable_evenly(PLAN_A_PRINCIPAL, 6, Money.from_rupees("22000.001"))


def test_split_total_payable_evenly_invalid_tenure_raises_invalid_emi_terms_error() -> None:
    """The tenure is checked before any division happens."""
    with pytest.raises(InvalidEmiTermsError) as raised_error:
        split_total_payable_evenly(PLAN_A_PRINCIPAL, 0, PLAN_A_PRINCIPAL)
    assert raised_error.value.code == "INVALID_EMI_TERMS"
