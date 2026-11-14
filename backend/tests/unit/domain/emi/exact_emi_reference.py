"""Exact reference EMI maths for tests, written independently of the production strategies.

It works in integer paise with fractions.Fraction, derives the EMI from the present value of the
installments and walks the balance month by month, so it shares no formula with the production
code. A result of None means no non-negative whole-paise schedule exists.
"""

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction


@dataclass(frozen=True)
class ReferenceSchedule:
    """An expected schedule in integer paise: tenure - 1 regular installments, then the last."""

    tenure_in_months: int
    regular_installment_in_paise: int
    last_installment_in_paise: int

    @property
    def total_payable_in_paise(self) -> int:
        """Gives the sum of all installments in paise."""
        return self.regular_installment_in_paise * (self.tenure_in_months - 1) + (
            self.last_installment_in_paise
        )


def round_half_up_to_whole_paise(exact_paise: Fraction) -> int:
    """Rounds a non-negative exact paise amount half-up to a whole number of paise."""
    return math.floor(exact_paise + Fraction(1, 2))


def reference_even_split(total_in_paise: int, tenure_in_months: int) -> ReferenceSchedule | None:
    """Splits a total evenly with half-up rounding; the last installment takes the remainder."""
    regular_in_paise = round_half_up_to_whole_paise(Fraction(total_in_paise, tenure_in_months))
    last_in_paise = total_in_paise - regular_in_paise * (tenure_in_months - 1)
    if last_in_paise < 0:
        return None
    return ReferenceSchedule(tenure_in_months, regular_in_paise, last_in_paise)


def reference_reducing_balance(
    principal_in_paise: int, tenure_in_months: int, annual_interest_rate_percent: Decimal
) -> ReferenceSchedule | None:
    """Amortises a loan month by month; the last installment clears the remaining balance."""
    if annual_interest_rate_percent.is_zero():
        return reference_even_split(principal_in_paise, tenure_in_months)
    monthly_growth = 1 + Fraction(annual_interest_rate_percent) / 1200
    present_value_of_one_per_month = sum(
        (monthly_growth**-month for month in range(1, tenure_in_months + 1)), Fraction(0)
    )
    regular_in_paise = round_half_up_to_whole_paise(
        Fraction(principal_in_paise) / present_value_of_one_per_month
    )
    balance_in_paise = Fraction(principal_in_paise)
    for _ in range(tenure_in_months - 1):
        balance_in_paise = balance_in_paise * monthly_growth - regular_in_paise
    final_amount_due_in_paise = balance_in_paise * monthly_growth
    if final_amount_due_in_paise < 0:
        return None
    return ReferenceSchedule(
        tenure_in_months, regular_in_paise, round_half_up_to_whole_paise(final_amount_due_in_paise)
    )
