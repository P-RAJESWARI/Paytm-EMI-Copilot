"""Tests for the Money value object: construction, half-up paise rounding and exact arithmetic."""

import dataclasses
from collections.abc import Callable
from decimal import Decimal, getcontext
from typing import Any, cast

import pytest

from emi_copilot.domain.errors import InvalidMoneyAmountError
from emi_copilot.domain.money import Money

MAXIMUM_AMOUNT_IN_PAISE = 2**63 - 1
REJECTED_NON_NUMERIC_VALUES: list[object] = [1.5, 0.0, True, False, None, [1]]
# Tamil digits ("\u0be7\u0be8") are display text, never machine amounts.
REJECTED_RUPEE_STRINGS = ["abc", "", " 12", "12 ", "1,000", "1_000", "1e3", "-5", "+5", ".5", "5."]
REJECTED_RUPEE_STRINGS += ["NaN", "Infinity", "\u0be7\u0be8"]
REJECTED_NUMBERS: list[object] = [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity")]
REJECTED_NUMBERS += [Decimal("-Infinity"), Decimal("-0.01"), Decimal("-0"), -1]


@pytest.mark.parametrize(
    ("rupee_value", "expected_amount_in_rupees"),
    [
        ("22000", Decimal("22000")),
        ("3666.67", Decimal("3666.67")),
        ("0", Decimal("0")),
        ("0.005", Decimal("0.005")),
        (22000, Decimal("22000")),
        (0, Decimal("0")),
        (Decimal("3666.666666"), Decimal("3666.666666")),
    ],
)
def test_money_from_rupees_valid_value_holds_exact_decimal(
    rupee_value: str | int | Decimal, expected_amount_in_rupees: Decimal
) -> None:
    """Strings, ints and Decimals are kept exactly, including sub-paise digits."""
    assert Money.from_rupees(rupee_value).amount_in_rupees == expected_amount_in_rupees


@pytest.mark.parametrize(
    "rejected_value",
    [*REJECTED_NON_NUMERIC_VALUES, *REJECTED_RUPEE_STRINGS, *REJECTED_NUMBERS],
)
def test_money_from_rupees_invalid_value_raises_invalid_money_amount_error(
    rejected_value: object,
) -> None:
    """Floats, bools, junk strings, non-finite and negative values never become Money."""
    with pytest.raises(InvalidMoneyAmountError):
        Money.from_rupees(cast("Any", rejected_value))


@pytest.mark.parametrize("rejected_value", [100.0, True, False, "100", Decimal(100), None, -1])
def test_money_from_paise_invalid_value_raises_invalid_money_amount_error(
    rejected_value: object,
) -> None:
    """Paise must be a non-negative int; floats, bools, strings and Decimals are refused."""
    with pytest.raises(InvalidMoneyAmountError):
        Money.from_paise(cast("Any", rejected_value))


@pytest.mark.parametrize("rejected_amount", [2.5, "2.5", 2, None])
def test_money_constructor_non_decimal_amount_raises_invalid_money_amount_error(
    rejected_amount: object,
) -> None:
    """Building Money directly is validated too, so it cannot bypass the named constructors."""
    with pytest.raises(InvalidMoneyAmountError):
        Money(cast("Any", rejected_amount))


def test_money_from_paise_converts_to_rupees() -> None:
    """366667 paise is 3666.67 rupees."""
    assert Money.from_paise(366667) == Money.from_rupees("3666.67")


def test_money_from_paise_maximum_bigint_value_is_accepted() -> None:
    """The largest signed 64-bit paise value is the largest storable amount."""
    assert Money.from_paise(MAXIMUM_AMOUNT_IN_PAISE).to_paise() == MAXIMUM_AMOUNT_IN_PAISE


def test_money_from_paise_above_bigint_limit_raises_invalid_money_amount_error() -> None:
    """Amounts that cannot be stored as BigInteger paise are rejected."""
    with pytest.raises(InvalidMoneyAmountError, match="BigInteger"):
        Money.from_paise(MAXIMUM_AMOUNT_IN_PAISE + 1)


def test_money_is_immutable() -> None:
    """A Value Object cannot be changed after it is created."""
    price = Money.from_rupees("22000")
    with pytest.raises(dataclasses.FrozenInstanceError):
        price.amount_in_rupees = Decimal(1)  # type: ignore[misc]


def test_money_equal_amounts_with_different_scales_are_equal_and_hash_alike() -> None:
    """Equality is numeric, so 22000 and 22000.00 are the same amount."""
    assert Money.from_rupees("22000") == Money.from_rupees("22000.00")
    assert hash(Money.from_rupees("22000")) == hash(Money.from_rupees("22000.00"))


@pytest.mark.parametrize(
    ("rupee_value", "expected_rounded_rupees"),
    [
        ("0.005", "0.01"),
        ("0.004", "0.00"),
        ("0.0049999", "0.00"),
        ("3666.665", "3666.67"),
        ("2.675", "2.68"),
        ("2.665", "2.67"),
        ("0.015", "0.02"),
        ("0.025", "0.03"),
        ("3666.67", "3666.67"),
    ],
)
def test_money_rounded_to_paise_half_up_boundary_rounds_half_away_from_zero(
    rupee_value: str, expected_rounded_rupees: str
) -> None:
    """Exact halves round up (never banker's rounding) and 2.675 shows no binary float artefact."""
    rounded = Money.from_rupees(rupee_value).rounded_to_paise()
    assert str(rounded) == expected_rounded_rupees


def test_money_to_paise_sub_paise_value_raises_invalid_money_amount_error() -> None:
    """Nothing rounds implicitly: sub-paise values must be rounded explicitly first."""
    with pytest.raises(InvalidMoneyAmountError, match="rounded_to_paise"):
        Money.from_rupees("3666.665").to_paise()


def test_money_to_paise_whole_paise_value_returns_integer_paise() -> None:
    """Whole-paise amounts convert exactly, including ones written with extra zeros."""
    assert Money.from_rupees("3666.67").to_paise() == 366667
    assert Money.from_rupees("3666.6700").to_paise() == 366667
    assert Money.from_rupees(22000).to_paise() == 2200000


def test_money_is_whole_paise_reports_sub_paise_precision() -> None:
    """Values with digits below one paisa are not whole paise."""
    assert Money.from_rupees("3666.67").is_whole_paise
    assert not Money.from_rupees("3666.665").is_whole_paise


def test_money_is_zero_reports_zero_amounts_only() -> None:
    """Zero is a valid amount (no-cost extra) and is recognisable without a signed result."""
    assert Money.from_paise(0).is_zero
    assert not Money.from_paise(1).is_zero


def test_money_design_sample_no_cost_plan_installments_sum_to_price() -> None:
    """22000 / 6 rounds to 3666.67, and the last installment 3666.65 absorbs the remainder."""
    price = Money.from_rupees("22000")
    monthly_installment = (price / 6).rounded_to_paise()
    last_installment = Money.from_rupees("22000.00") - 5 * monthly_installment
    assert monthly_installment == Money.from_rupees("3666.67")
    assert last_installment == Money.from_rupees("3666.65")
    assert 5 * monthly_installment + last_installment == price


def test_money_multiply_and_divide_keep_sub_paise_precision() -> None:
    """Intermediate results are not rounded until rounded_to_paise() is called."""
    third = Money.from_rupees("1") / 3
    assert not third.is_whole_paise
    assert (third * 3).rounded_to_paise() == Money.from_rupees("1.00")
    assert Money.from_rupees("100") * Decimal("0.015") == Money.from_rupees("1.5")
    assert Money.from_rupees("100") / Decimal("2.5") == Money.from_rupees("40")


def test_money_subtraction_below_zero_raises_invalid_money_amount_error() -> None:
    """Money is never negative, so subtracting a larger amount is a bug that raises."""
    with pytest.raises(InvalidMoneyAmountError, match="negative"):
        Money.from_rupees("1") - Money.from_rupees("1.01")


def test_money_subtraction_of_equal_amounts_is_zero() -> None:
    """Subtracting an amount from itself gives exactly zero."""
    assert (Money.from_rupees("3666.67") - Money.from_rupees("3666.67")).is_zero


def test_money_divide_by_zero_raises_invalid_money_amount_error() -> None:
    """Division by zero is a typed domain error, not a decimal module exception."""
    with pytest.raises(InvalidMoneyAmountError, match="zero"):
        Money.from_rupees("22000") / 0
    with pytest.raises(InvalidMoneyAmountError, match="zero"):
        Money.from_rupees("22000") / Decimal("0.00")


@pytest.mark.parametrize("negative_factor", [-1, Decimal("-0.5")])
def test_money_multiply_or_divide_by_negative_raises_invalid_money_amount_error(
    negative_factor: int | Decimal,
) -> None:
    """A negative factor would make a negative amount, which is rejected."""
    with pytest.raises(InvalidMoneyAmountError):
        Money.from_rupees("10") * negative_factor
    with pytest.raises(InvalidMoneyAmountError):
        Money.from_rupees("10") / negative_factor


@pytest.mark.parametrize(
    "rejected_operation",
    [
        lambda money, value: money + value,
        lambda money, value: money - value,
        lambda money, value: money * value,
        lambda money, value: value * money,
        lambda money, value: money / value,
    ],
    ids=["add", "subtract", "multiply", "reflected-multiply", "divide"],
)
@pytest.mark.parametrize(
    "rejected_operand",
    [1.5, True, Decimal("NaN"), Decimal("Infinity"), "2", None],
    ids=["float", "bool", "nan", "infinity", "string", "none"],
)
def test_money_operator_invalid_operand_raises_invalid_money_amount_error(
    rejected_operation: Callable[[Money, Any], Money], rejected_operand: object
) -> None:
    """Every operator with Money on the left (and int * Money) rejects floats, bools and junk."""
    with pytest.raises(InvalidMoneyAmountError):
        rejected_operation(Money.from_rupees("10"), rejected_operand)


def test_money_add_or_subtract_plain_number_raises_invalid_money_amount_error() -> None:
    """Only Money can be added to Money; a bare int or Decimal has no unit."""
    with pytest.raises(InvalidMoneyAmountError):
        Money.from_rupees("10") + 5  # type: ignore[operator]
    with pytest.raises(InvalidMoneyAmountError):
        Money.from_rupees("10") - Decimal(5)  # type: ignore[operator]


@pytest.mark.parametrize(
    "reflected_operation",
    [
        lambda money: 1.5 + money,
        lambda money: 1.5 - money,
        lambda money: 1.5 / money,
        lambda money: money < 1.5,
    ],
    ids=["reflected-add", "reflected-subtract", "reflected-divide", "compare"],
)
def test_money_float_on_left_or_in_comparison_raises_type_error(
    reflected_operation: Callable[[Any], object],
) -> None:
    """Python refuses these mixes: Money defines no reflected add, subtract or divide."""
    with pytest.raises(TypeError):
        reflected_operation(Money.from_rupees("10"))


def test_money_comparisons_order_by_amount() -> None:
    """Amounts compare and sort numerically."""
    smaller = Money.from_rupees("3666.65")
    larger = Money.from_rupees("3666.67")
    assert smaller < larger
    assert larger > smaller
    assert smaller <= Money.from_rupees("3666.650")
    assert sorted([larger, smaller]) == [smaller, larger]


def test_money_arithmetic_does_not_change_global_decimal_context() -> None:
    """Money uses its own context, so global precision and rounding are left untouched."""
    global_context_before = getcontext().copy()
    _ = (Money.from_rupees("22000") / 7).rounded_to_paise()
    global_context_after = getcontext()
    assert global_context_after.prec == global_context_before.prec
    assert global_context_after.rounding == global_context_before.rounding


def test_money_division_is_precise_beyond_global_default_precision() -> None:
    """Division keeps 34 significant digits, more than the global default of 28."""
    third = Money.from_rupees("1") / 3
    assert str(third) == "0." + "3" * 34


def test_money_str_shows_plain_decimal_without_exponent() -> None:
    """Text never uses float formatting or scientific notation."""
    assert str(Money.from_rupees("2.675")) == "2.675"
    assert str(Money.from_rupees(Decimal("2.2E+4"))) == "22000"
    assert str(Money.from_paise(366667)) == "3666.67"


def test_money_repr_shows_how_to_rebuild_the_amount() -> None:
    """The representation is exact and rebuilds an equal Money."""
    price = Money.from_rupees("3666.67")
    assert repr(price) == "Money.from_rupees('3666.67')"
