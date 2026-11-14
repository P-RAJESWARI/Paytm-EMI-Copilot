"""Reducing-balance EMI: the standard amortising installment for an annual interest rate."""

from decimal import ROUND_HALF_UP, Context, Decimal, DivisionByZero, InvalidOperation, Overflow
from fractions import Fraction

from emi_copilot.domain.emi.emi_calculation_strategy import EmiCalculationStrategy
from emi_copilot.domain.emi.emi_schedule import (
    EmiSchedule,
    require_valid_emi_terms,
    split_total_payable_evenly,
)
from emi_copilot.domain.errors import EmiScheduleNotRepresentableError, InvalidEmiTermsError
from emi_copilot.domain.money import Money

_PERCENT_PER_YEAR_TO_FRACTION_PER_MONTH = 1200
# A private context, so the thread's global Decimal context is never read or mutated. Its 34
# digits (Money's precision) only matter for non-terminating values; amounts that end within 34
# digits, such as an exact half paisa, convert exactly, so the later half-up rounding is correct.
_EXACT_TO_DECIMAL_CONTEXT = Context(
    prec=34, rounding=ROUND_HALF_UP, traps=[DivisionByZero, InvalidOperation, Overflow]
)


def _money_from_exact_rupees(exact_rupees: Fraction) -> Money:
    """Converts an exact non-negative rupee amount to Money, still unrounded to paise."""
    return Money(
        _EXACT_TO_DECIMAL_CONTEXT.divide(
            Decimal(exact_rupees.numerator), Decimal(exact_rupees.denominator)
        )
    )


def _require_valid_annual_interest_rate(annual_interest_rate_percent: object) -> None:
    """Raises unless the rate is a finite, non-negative Decimal percentage per year."""
    if not isinstance(annual_interest_rate_percent, Decimal):
        raise InvalidEmiTermsError("The annual interest rate must be a Decimal percentage.")
    if not annual_interest_rate_percent.is_finite():
        raise InvalidEmiTermsError("The annual interest rate must be finite.")
    if annual_interest_rate_percent.is_signed():
        raise InvalidEmiTermsError("The annual interest rate cannot be negative.")


class ReducingBalanceStrategy(EmiCalculationStrategy):
    """Amortises the principal at a monthly rate of annual percent / 1200 (rate-quoted offers).

    The maths runs on exact fractions because 1/1200 has no finite decimal expansion; a rounded
    rate could move an installment that sits exactly on a half paisa. A 0% rate is no-cost.
    """

    def __init__(self, annual_interest_rate_percent: Decimal) -> None:
        """Stores the annual rate as a percentage, for example Decimal('16.9449')."""
        _require_valid_annual_interest_rate(annual_interest_rate_percent)
        self._annual_interest_rate_percent = annual_interest_rate_percent

    @property
    def annual_interest_rate_percent(self) -> Decimal:
        """Gives the annual interest rate as a percentage."""
        return self._annual_interest_rate_percent

    def calculate_schedule(self, principal: Money, tenure_in_months: int) -> EmiSchedule:
        """Calculates EMI = P·r·(1+r)^n / ((1+r)^n - 1); the last pays off the exact balance."""
        require_valid_emi_terms(principal, tenure_in_months)
        if self._annual_interest_rate_percent.is_zero():
            return split_total_payable_evenly(principal, tenure_in_months, total_payable=principal)
        monthly_rate = (
            Fraction(self._annual_interest_rate_percent) / _PERCENT_PER_YEAR_TO_FRACTION_PER_MONTH
        )
        growth_factor = (1 + monthly_rate) ** tenure_in_months
        principal_in_rupees = Fraction(principal.amount_in_rupees)
        exact_installment = principal_in_rupees * monthly_rate * growth_factor / (growth_factor - 1)
        regular_installment = _money_from_exact_rupees(exact_installment).rounded_to_paise()
        exact_last_installment = _calculate_exact_last_installment(
            principal_in_rupees,
            Fraction(regular_installment.amount_in_rupees),
            monthly_rate,
            growth_factor,
        )
        return EmiSchedule(
            principal=principal,
            tenure_in_months=tenure_in_months,
            regular_installment=regular_installment,
            last_installment=_money_from_exact_rupees(exact_last_installment).rounded_to_paise(),
        )


def _calculate_exact_last_installment(
    principal_in_rupees: Fraction,
    regular_installment_in_rupees: Fraction,
    monthly_rate: Fraction,
    growth_factor: Fraction,
) -> Fraction:
    """Gives the balance left after n - 1 regular installments, plus its final month's interest.

    That is P·(1+r)^n minus each regular installment grown to month n, whose sum is
    R·((1+r)^n - (1+r)) / r. Raises when the regular installments alone overpay the loan.
    """
    regular_installments_grown_to_last_month = (
        regular_installment_in_rupees * (growth_factor - (1 + monthly_rate)) / monthly_rate
    )
    exact_last_installment = principal_in_rupees * growth_factor - (
        regular_installments_grown_to_last_month
    )
    if exact_last_installment < 0:
        raise EmiScheduleNotRepresentableError(
            "The rounded regular installments overpay this loan before the last month, so the "
            "last installment would be negative."
        )
    return exact_last_installment
