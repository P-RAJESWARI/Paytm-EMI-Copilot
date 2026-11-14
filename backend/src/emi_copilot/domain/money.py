"""Money value object: exact Decimal rupee amounts, converted to integer paise at the boundary."""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal, DivisionByZero, InvalidOperation, Overflow

from emi_copilot.domain.errors import InvalidMoneyAmountError

# Money owns its arithmetic context so the thread's global Decimal context is never read or
# mutated. 34 significant digits (IEEE decimal128) leave ample room for sub-paise EMI maths.
_MONEY_PRECISION_IN_DIGITS = 34
_MONEY_ARITHMETIC_CONTEXT = Context(
    prec=_MONEY_PRECISION_IN_DIGITS,
    rounding=ROUND_HALF_UP,
    traps=[DivisionByZero, InvalidOperation, Overflow],
)
# Paise are stored in a signed 64-bit BigInteger column, so every amount must fit in one. That
# cap also leaves at least 15 significant digits below one paisa for intermediate EMI maths.
_MAXIMUM_AMOUNT_IN_PAISE = 2**63 - 1
_MAXIMUM_AMOUNT_IN_RUPEES = Decimal(_MAXIMUM_AMOUNT_IN_PAISE).scaleb(-2, _MONEY_ARITHMETIC_CONTEXT)
_ONE_PAISA_IN_RUPEES = Decimal("0.01")
_PAISE_PER_RUPEE = 100
_PLAIN_RUPEE_STRING_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def _reject_float_and_bool(value: object) -> None:
    """Raises when a value is a float or a bool, neither of which may ever become money."""
    if isinstance(value, bool):
        raise InvalidMoneyAmountError("A bool is not a money amount.")
    if isinstance(value, float):
        raise InvalidMoneyAmountError(
            "A float is never accepted for money; use str, int or Decimal."
        )


def _parse_rupee_amount(value: object) -> Decimal:
    """Converts a str, int or Decimal rupee value into a Decimal without rounding it."""
    _reject_float_and_bool(value)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        if _PLAIN_RUPEE_STRING_PATTERN.fullmatch(value) is None:
            raise InvalidMoneyAmountError(
                f"Rupee strings must be plain non-negative decimals like '3666.67', got {value!r}."
            )
        return Decimal(value)
    raise InvalidMoneyAmountError(f"A {type(value).__name__} is not a money amount.")


def _parse_factor(value: object) -> Decimal:
    """Validates a multiplier or divisor, which must be an int or a finite Decimal."""
    _reject_float_and_bool(value)
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, Decimal) and value.is_finite():
        return value
    raise InvalidMoneyAmountError("Money can only be multiplied or divided by an int or Decimal.")


def _validate_amount_in_rupees(amount_in_rupees: object) -> None:
    """Raises unless the amount is a finite, non-negative Decimal that fits in BigInteger paise."""
    if not isinstance(amount_in_rupees, Decimal):
        raise InvalidMoneyAmountError("Money must hold a Decimal amount in rupees.")
    if not amount_in_rupees.is_finite():
        raise InvalidMoneyAmountError("Money must be finite; NaN and Infinity are rejected.")
    if amount_in_rupees.is_signed():
        raise InvalidMoneyAmountError(f"Money cannot be negative, got {amount_in_rupees:f}.")
    if amount_in_rupees > _MAXIMUM_AMOUNT_IN_RUPEES:
        raise InvalidMoneyAmountError(
            f"Money cannot exceed {_MAXIMUM_AMOUNT_IN_RUPEES:f} rupees (BigInteger paise limit)."
        )


def _require_money(value: object) -> None:
    """Raises unless the other operand of an addition or subtraction is Money."""
    _reject_float_and_bool(value)
    if not isinstance(value, Money):
        raise InvalidMoneyAmountError("Money can only be added to or subtracted from Money.")


# Pattern: Value Object. Immutable, validated on creation and the single owner of paise rounding.
@dataclass(frozen=True, slots=True, order=True)
class Money:
    """A non-negative rupee amount (INR is implied) held as an exact Decimal.

    Negative amounts are rejected: prices, installments, totals and remainders are never below
    zero, so a subtraction that would go negative is a bug and raises. Use `is_zero` and the
    comparison operators instead of signed results. Amounts above 2**63 - 1 paise (the BigInteger
    column limit) are rejected too. Sub-paise precision is kept for intermediate EMI maths, to 34
    significant digits; `rounded_to_paise()` is the only rounding to paise (half-up), and
    `to_paise()` refuses sub-paise values so nothing is ever rounded implicitly.
    """

    amount_in_rupees: Decimal

    def __post_init__(self) -> None:
        """Rejects any amount that is not a finite, non-negative Decimal."""
        _validate_amount_in_rupees(self.amount_in_rupees)

    @classmethod
    def from_rupees(cls, value: str | int | Decimal) -> "Money":
        """Builds Money from rupees given as a plain decimal string, an int or a Decimal."""
        return cls(_parse_rupee_amount(value))

    @classmethod
    def from_paise(cls, value: int) -> "Money":
        """Builds Money from an integer number of paise, as read from the database or the wire."""
        _reject_float_and_bool(value)
        if not isinstance(value, int):
            raise InvalidMoneyAmountError("Paise must be an int.")
        return cls(Decimal(value).scaleb(-2, _MONEY_ARITHMETIC_CONTEXT))

    @property
    def is_zero(self) -> bool:
        """Tells whether the amount is exactly zero rupees."""
        return self.amount_in_rupees.is_zero()

    @property
    def is_whole_paise(self) -> bool:
        """Tells whether the amount has no precision below one paisa."""
        return self.rounded_to_paise() == self

    def rounded_to_paise(self) -> "Money":
        """Rounds half-up to the nearest paisa; the one and only rounding operation for money."""
        rounded_amount_in_rupees = self.amount_in_rupees.quantize(
            _ONE_PAISA_IN_RUPEES, rounding=ROUND_HALF_UP, context=_MONEY_ARITHMETIC_CONTEXT
        )
        return Money(rounded_amount_in_rupees)

    def to_paise(self) -> int:
        """Converts a whole-paise amount to integer paise; round with rounded_to_paise() first."""
        if not self.is_whole_paise:
            raise InvalidMoneyAmountError(
                f"{self} has sub-paise precision; call rounded_to_paise() before to_paise()."
            )
        return int(_MONEY_ARITHMETIC_CONTEXT.multiply(self.amount_in_rupees, _PAISE_PER_RUPEE))

    def __add__(self, other: "Money") -> "Money":
        """Adds two amounts exactly."""
        _require_money(other)
        return Money(_MONEY_ARITHMETIC_CONTEXT.add(self.amount_in_rupees, other.amount_in_rupees))

    def __sub__(self, other: "Money") -> "Money":
        """Subtracts an amount; raises if the result would be negative."""
        _require_money(other)
        return Money(
            _MONEY_ARITHMETIC_CONTEXT.subtract(self.amount_in_rupees, other.amount_in_rupees)
        )

    def __mul__(self, factor: int | Decimal) -> "Money":
        """Multiplies the amount by an int or Decimal factor, keeping sub-paise precision."""
        return Money(
            _MONEY_ARITHMETIC_CONTEXT.multiply(self.amount_in_rupees, _parse_factor(factor))
        )

    def __rmul__(self, factor: int | Decimal) -> "Money":
        """Supports `factor * money` with the same rules as `money * factor`."""
        return self * factor

    def __truediv__(self, divisor: int | Decimal) -> "Money":
        """Divides the amount by a non-zero int or Decimal, keeping sub-paise precision."""
        divisor_as_decimal = _parse_factor(divisor)
        if divisor_as_decimal.is_zero():
            raise InvalidMoneyAmountError("Money cannot be divided by zero.")
        return Money(_MONEY_ARITHMETIC_CONTEXT.divide(self.amount_in_rupees, divisor_as_decimal))

    def __str__(self) -> str:
        """Shows the exact rupee amount in plain decimal notation, for logs and debugging only."""
        return format(self.amount_in_rupees, "f")

    def __repr__(self) -> str:
        """Shows how to rebuild this exact amount."""
        return f"Money.from_rupees('{self}')"
