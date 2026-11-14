"""Hand-checked reference schedules, including the three design plans on ₹22,000 (ADR 0001).

Every expected value is hard-coded. Even splits were checked by hand (for example 22,000 / 6 =
3,666.666... -> 3,666.67, and 22,000 - 5 x 3,666.67 = 3,666.65). Reducing-balance rows were
computed with exact fractions month by month and agree with common published EMI figures
(₹1,00,000 at 12% for 12 months is ₹8,884.88; ₹50,000 at 10.5% for 24 months is ₹2,318.80).
"""

from collections.abc import Callable
from decimal import Decimal
from typing import NamedTuple

import pytest

from emi_copilot.domain.emi import (
    EmiCalculationStrategy,
    NoCostStrategy,
    QuotedTotalStrategy,
    ReducingBalanceStrategy,
)
from emi_copilot.domain.money import Money
from tests.unit.domain.emi.exact_emi_reference import reference_reducing_balance

StrategyFactory = Callable[[], EmiCalculationStrategy]


def no_cost() -> StrategyFactory:
    """Builds a factory for the no-cost strategy."""
    return NoCostStrategy


def quoted_extra(extra_in_paise: int) -> StrategyFactory:
    """Builds a factory for a quoted-total strategy with the given extra in paise."""
    return lambda: QuotedTotalStrategy(Money.from_paise(extra_in_paise))


def reducing_balance(annual_rate_percent: str) -> StrategyFactory:
    """Builds a factory for a reducing-balance strategy at the given annual percentage."""
    return lambda: ReducingBalanceStrategy(Decimal(annual_rate_percent))


class ReferenceRow(NamedTuple):
    """One hand-checked schedule; every amount is in paise."""

    name: str
    strategy_factory: StrategyFactory
    principal_in_paise: int
    tenure_in_months: int
    regular_installment_in_paise: int
    last_installment_in_paise: int
    total_payable_in_paise: int
    extra_in_total_in_paise: int


Row = ReferenceRow
# Columns: name, strategy, principal, tenure, regular, last, total, extra (amounts in paise).
REFERENCE_TABLE = [
    Row("design plan A no-cost", no_cost(), 2200000, 6, 366667, 366665, 2200000, 0),
    Row("design plan B quoted", quoted_extra(110000), 2200000, 6, 385000, 385000, 2310000, 110000),
    Row("design plan C quoted", quoted_extra(260000), 2200000, 12, 205000, 205000, 2460000, 260000),
    Row("no-cost remainder up", no_cost(), 1000000, 3, 333333, 333334, 1000000, 0),
    Row("no-cost one month", no_cost(), 2200000, 1, 2200000, 2200000, 2200000, 0),
    Row("quoted remainder up", quoted_extra(100000), 1800000, 9, 211111, 211112, 1900000, 100000),
    Row("quoted remainder down", quoted_extra(12345), 1000000, 7, 144621, 144619, 1012345, 12345),
    Row("rate 12%", reducing_balance("12"), 10000000, 12, 888488, 888487, 10661855, 661855),
    Row("rate 15%", reducing_balance("15"), 2200000, 12, 198568, 198572, 2382820, 182820),
    Row("rate 10.5%", reducing_balance("10.5"), 5000000, 24, 231880, 231886, 5565126, 565126),
    Row("rate 8.75%", reducing_balance("8.75"), 50000000, 60, 1031862, 1031835, 61911693, 11911693),
    Row("rate 36%", reducing_balance("36"), 1500000, 9, 192651, 192649, 1733857, 233857),
    Row("rate 40%", reducing_balance("40"), 2200000, 6, 410613, 410610, 2463675, 263675),
    Row("rate 18% odd paise", reducing_balance("18"), 99999, 3, 34338, 34338, 103014, 3015),
    Row("rate 24% one month", reducing_balance("24"), 100000, 1, 102000, 102000, 102000, 2000),
    Row("rate 0% is no-cost", reducing_balance("0"), 2200000, 6, 366667, 366665, 2200000, 0),
    # 60,000 x 0.0001% / 1200 is exactly half a paisa of interest, so half-up adds one paisa.
    Row("exact half paisa", reducing_balance("0.0001"), 6000000, 1, 6000001, 6000001, 6000001, 1),
    Row("rate 16.9449%", reducing_balance("16.9449"), 2200000, 6, 385000, 385000, 2310000, 110000),
]  # fmt: skip
REDUCING_BALANCE_ROWS = [row for row in REFERENCE_TABLE if row.name.startswith(("rate", "exact"))]


@pytest.mark.parametrize("row", REFERENCE_TABLE, ids=[row.name for row in REFERENCE_TABLE])
def test_emi_strategy_reference_row_matches_hand_checked_schedule(row: ReferenceRow) -> None:
    """Each strategy reproduces the hand-checked regular, last, total and extra to the paisa."""
    schedule = row.strategy_factory().calculate_schedule(
        Money.from_paise(row.principal_in_paise), row.tenure_in_months
    )

    assert schedule.regular_installment.to_paise() == row.regular_installment_in_paise
    assert schedule.last_installment.to_paise() == row.last_installment_in_paise
    assert schedule.total_payable.to_paise() == row.total_payable_in_paise
    assert schedule.extra_in_total.to_paise() == row.extra_in_total_in_paise
    assert len(schedule.installments) == row.tenure_in_months


def test_design_plan_a_displays_3667_and_sums_to_exactly_22000() -> None:
    """Plan A is 5 x ₹3,666.67 + ₹3,666.65: it displays as ₹3,667 and sums to ₹22,000.00."""
    schedule = NoCostStrategy().calculate_schedule(Money.from_rupees("22000"), 6)

    assert schedule.installments == (Money.from_rupees("3666.67"),) * 5 + (
        Money.from_rupees("3666.65"),
    )
    assert schedule.total_payable == Money.from_rupees("22000.00")
    assert schedule.extra_in_total.is_zero


def test_reducing_balance_at_16_9449_percent_regular_installment_is_within_one_paisa_of_3850() -> (
    None
):
    """Cross-check of plan B by rate: the exact EMI is ₹3,850.000211..., so it rounds to ₹3,850.00.

    The last installment's exact amount due is ₹3,850.001312..., which also rounds to ₹3,850.00.
    """
    schedule = ReducingBalanceStrategy(Decimal("16.9449")).calculate_schedule(
        Money.from_rupees("22000"), 6
    )

    regular_difference_in_paise = schedule.regular_installment.to_paise() - 385000
    assert abs(regular_difference_in_paise) <= 1
    assert schedule.regular_installment == Money.from_rupees("3850.00")
    assert schedule.last_installment == Money.from_rupees("3850.00")


@pytest.mark.parametrize(
    "row", REDUCING_BALANCE_ROWS, ids=[row.name for row in REDUCING_BALANCE_ROWS]
)
def test_exact_emi_reference_reproduces_hand_checked_reducing_balance_rows(
    row: ReferenceRow,
) -> None:
    """The exact test oracle used by the property tests agrees with the hard-coded table."""
    strategy = row.strategy_factory()
    assert isinstance(strategy, ReducingBalanceStrategy)

    reference = reference_reducing_balance(
        row.principal_in_paise, row.tenure_in_months, strategy.annual_interest_rate_percent
    )

    assert reference is not None
    assert reference.regular_installment_in_paise == row.regular_installment_in_paise
    assert reference.last_installment_in_paise == row.last_installment_in_paise
    assert reference.total_payable_in_paise == row.total_payable_in_paise
