"""Tests for each EMI strategy's input validation and its specific behaviour."""

from decimal import Decimal
from typing import Any, cast

import pytest

from emi_copilot.domain.emi import (
    EmiCalculationStrategy,
    NoCostStrategy,
    QuotedTotalStrategy,
    ReducingBalanceStrategy,
)
from emi_copilot.domain.errors import EmiScheduleNotRepresentableError, InvalidEmiTermsError
from emi_copilot.domain.money import Money

PLAN_A_PRINCIPAL = Money.from_rupees("22000")
ALL_STRATEGIES: list[EmiCalculationStrategy] = [
    NoCostStrategy(),
    QuotedTotalStrategy(Money.from_rupees("1100")),
    ReducingBalanceStrategy(Decimal("12")),
]
ALL_STRATEGY_IDS = ["no-cost", "quoted-total", "reducing-balance"]


@pytest.mark.parametrize("strategy", ALL_STRATEGIES, ids=ALL_STRATEGY_IDS)
@pytest.mark.parametrize("invalid_tenure_in_months", [0, -1, -12])
def test_emi_strategy_tenure_below_one_month_raises_invalid_emi_terms_error(
    strategy: EmiCalculationStrategy, invalid_tenure_in_months: int
) -> None:
    """No strategy calculates a schedule for a zero or negative tenure."""
    with pytest.raises(InvalidEmiTermsError):
        strategy.calculate_schedule(PLAN_A_PRINCIPAL, invalid_tenure_in_months)


@pytest.mark.parametrize("strategy", ALL_STRATEGIES, ids=ALL_STRATEGY_IDS)
@pytest.mark.parametrize(
    "invalid_principal",
    [Money.from_paise(0), Money.from_rupees("100.001"), "22000"],
    ids=["zero", "sub-paise", "not money"],
)
def test_emi_strategy_invalid_principal_raises_invalid_emi_terms_error(
    strategy: EmiCalculationStrategy, invalid_principal: object
) -> None:
    """Every strategy rejects a principal that is zero, sub-paise or not Money."""
    with pytest.raises(InvalidEmiTermsError):
        strategy.calculate_schedule(cast(Any, invalid_principal), 6)


@pytest.mark.parametrize(
    "strategy",
    [
        NoCostStrategy(),
        QuotedTotalStrategy(Money.from_rupees("0.10")),
        ReducingBalanceStrategy(Decimal("1")),
    ],
    ids=ALL_STRATEGY_IDS,
)
def test_emi_strategy_tiny_principal_over_long_tenure_raises_not_representable(
    strategy: EmiCalculationStrategy,
) -> None:
    """₹1 over 60 months rounds each regular installment up to ₹0.02, and 59 of them overpay."""
    with pytest.raises(EmiScheduleNotRepresentableError):
        strategy.calculate_schedule(Money.from_rupees("1"), 60)


def test_quoted_total_strategy_zero_extra_gives_no_cost_schedule() -> None:
    """A quoted extra of zero rupees behaves exactly like a no-cost plan."""
    quoted_schedule = QuotedTotalStrategy(Money.from_paise(0)).calculate_schedule(
        PLAN_A_PRINCIPAL, 6
    )

    assert quoted_schedule == NoCostStrategy().calculate_schedule(PLAN_A_PRINCIPAL, 6)


def test_quoted_total_strategy_exposes_quoted_extra_in_total() -> None:
    """The strategy keeps the lender's quoted extra unchanged."""
    assert QuotedTotalStrategy(Money.from_rupees("2600")).quoted_extra_in_total == (
        Money.from_rupees("2600")
    )


@pytest.mark.parametrize(
    "invalid_quoted_extra",
    [Money.from_rupees("1100.005"), 1100, "1100", Decimal("1100")],
    ids=["sub-paise", "int", "str", "decimal"],
)
def test_quoted_total_strategy_invalid_quoted_extra_raises_invalid_emi_terms_error(
    invalid_quoted_extra: object,
) -> None:
    """The quoted extra must be whole-paise Money."""
    with pytest.raises(InvalidEmiTermsError):
        QuotedTotalStrategy(cast(Any, invalid_quoted_extra))


@pytest.mark.parametrize(
    "invalid_rate",
    [
        Decimal("-0.01"),
        Decimal("-0"),
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        16.9449,
        12,
        "12",
    ],
    ids=["negative", "negative zero", "nan", "signalling nan", "infinity", "float", "int", "str"],
)
def test_reducing_balance_strategy_invalid_rate_raises_invalid_emi_terms_error(
    invalid_rate: object,
) -> None:
    """The annual rate must be a finite, non-negative Decimal; floats are never accepted."""
    with pytest.raises(InvalidEmiTermsError):
        ReducingBalanceStrategy(cast(Any, invalid_rate))


def test_reducing_balance_strategy_exposes_annual_interest_rate_percent() -> None:
    """The strategy keeps the annual percentage unchanged."""
    strategy = ReducingBalanceStrategy(Decimal("16.9449"))

    assert strategy.annual_interest_rate_percent == Decimal("16.9449")


@pytest.mark.parametrize("tenure_in_months", [1, 6, 7, 60])
def test_reducing_balance_strategy_zero_rate_equals_no_cost_schedule(
    tenure_in_months: int,
) -> None:
    """A 0% rate charges nothing extra, exactly like a no-cost plan."""
    schedule = ReducingBalanceStrategy(Decimal("0")).calculate_schedule(
        PLAN_A_PRINCIPAL, tenure_in_months
    )

    assert schedule == NoCostStrategy().calculate_schedule(PLAN_A_PRINCIPAL, tenure_in_months)
    assert schedule.extra_in_total.is_zero


def test_reducing_balance_strategy_positive_rate_total_exceeds_principal() -> None:
    """Any positive rate on a realistic loan makes the customer pay something extra."""
    schedule = ReducingBalanceStrategy(Decimal("1")).calculate_schedule(PLAN_A_PRINCIPAL, 12)

    assert schedule.total_payable > PLAN_A_PRINCIPAL
