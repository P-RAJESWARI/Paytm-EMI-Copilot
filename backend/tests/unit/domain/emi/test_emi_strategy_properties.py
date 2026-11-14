"""Property-based tests for every EMI strategy over realistic inputs (testing.md section 3).

Ranges: principal ₹1 to ₹10,00,000 in whole paise, tenure 1 to 60 months, annual rate 0% to 40%
in steps of 0.0001%, and a quoted extra of 0% to 50% of the principal. Every schedule is compared
with the independent exact oracle, which also says when no valid schedule exists.
"""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.domain.emi import (
    EmiCalculationStrategy,
    EmiSchedule,
    NoCostStrategy,
    QuotedTotalStrategy,
    ReducingBalanceStrategy,
)
from emi_copilot.domain.errors import EmiScheduleNotRepresentableError
from emi_copilot.domain.money import Money
from tests.unit.domain.emi.exact_emi_reference import (
    ReferenceSchedule,
    reference_even_split,
    reference_reducing_balance,
)

PRINCIPAL_IN_PAISE = st.integers(min_value=100, max_value=100_000_000)
TENURE_IN_MONTHS = st.integers(min_value=1, max_value=60)
ANNUAL_RATE_PERCENT = st.integers(min_value=0, max_value=400_000).map(
    lambda rate_in_ten_thousandths: Decimal(rate_in_ten_thousandths).scaleb(-4)
)
ZERO_RUPEES = Money.from_paise(0)


def calculate_or_none(
    strategy: EmiCalculationStrategy, principal_in_paise: int, tenure_in_months: int
) -> EmiSchedule | None:
    """Runs a strategy, returning None when it reports that no valid schedule exists."""
    try:
        return strategy.calculate_schedule(Money.from_paise(principal_in_paise), tenure_in_months)
    except EmiScheduleNotRepresentableError:
        return None


def assert_schedule_invariants(schedule: EmiSchedule, tenure_in_months: int) -> None:
    """Checks the invariants every schedule must hold, whatever its strategy."""
    assert len(schedule.installments) == tenure_in_months
    assert all(installment.is_whole_paise for installment in schedule.installments)
    assert all(installment >= ZERO_RUPEES for installment in schedule.installments)
    assert sum(schedule.installments, ZERO_RUPEES) == schedule.total_payable
    assert schedule.total_payable >= schedule.principal
    assert schedule.total_payable - schedule.principal == schedule.extra_in_total


def assert_schedule_matches_reference(
    schedule: EmiSchedule | None, reference: ReferenceSchedule | None, tenure_in_months: int
) -> None:
    """Checks the strategy agrees with the oracle, including on when no schedule exists."""
    if reference is None:
        assert schedule is None
        return
    assert schedule is not None
    assert_schedule_invariants(schedule, tenure_in_months)
    assert schedule.regular_installment.to_paise() == reference.regular_installment_in_paise
    assert schedule.last_installment.to_paise() == reference.last_installment_in_paise


@given(principal_in_paise=PRINCIPAL_IN_PAISE, tenure_in_months=TENURE_IN_MONTHS)
def test_no_cost_strategy_any_valid_terms_matches_reference_with_zero_extra(
    principal_in_paise: int, tenure_in_months: int
) -> None:
    """No-cost schedules sum to exactly the principal, so the extra in total is exactly zero."""
    schedule = calculate_or_none(NoCostStrategy(), principal_in_paise, tenure_in_months)

    reference = reference_even_split(principal_in_paise, tenure_in_months)
    assert_schedule_matches_reference(schedule, reference, tenure_in_months)
    if schedule is not None:
        assert schedule.extra_in_total.is_zero
        assert schedule.total_payable.to_paise() == principal_in_paise


@given(data=st.data(), principal_in_paise=PRINCIPAL_IN_PAISE, tenure_in_months=TENURE_IN_MONTHS)
def test_quoted_total_strategy_any_valid_terms_matches_reference_with_quoted_extra(
    data: st.DataObject, principal_in_paise: int, tenure_in_months: int
) -> None:
    """Quoted-total schedules sum to principal plus the quoted extra, to the paisa."""
    extra_in_paise = data.draw(st.integers(min_value=0, max_value=principal_in_paise // 2))
    strategy = QuotedTotalStrategy(Money.from_paise(extra_in_paise))

    schedule = calculate_or_none(strategy, principal_in_paise, tenure_in_months)

    reference = reference_even_split(principal_in_paise + extra_in_paise, tenure_in_months)
    assert_schedule_matches_reference(schedule, reference, tenure_in_months)
    if schedule is not None:
        assert schedule.extra_in_total.to_paise() == extra_in_paise


@given(
    principal_in_paise=PRINCIPAL_IN_PAISE,
    tenure_in_months=TENURE_IN_MONTHS,
    annual_rate_percent=ANNUAL_RATE_PERCENT,
)
def test_reducing_balance_strategy_any_valid_terms_matches_exact_amortisation(
    principal_in_paise: int, tenure_in_months: int, annual_rate_percent: Decimal
) -> None:
    """Reducing-balance schedules match exact amortisation and never total below the principal."""
    strategy = ReducingBalanceStrategy(annual_rate_percent)

    schedule = calculate_or_none(strategy, principal_in_paise, tenure_in_months)

    reference = reference_reducing_balance(
        principal_in_paise, tenure_in_months, annual_rate_percent
    )
    assert_schedule_matches_reference(schedule, reference, tenure_in_months)


@pytest.mark.parametrize(
    "strategy",
    [
        NoCostStrategy(),
        QuotedTotalStrategy(Money.from_rupees("1100")),
        ReducingBalanceStrategy(Decimal("16.9449")),
    ],
    ids=["no-cost", "quoted-total", "reducing-balance"],
)
@given(principal_in_paise=PRINCIPAL_IN_PAISE, tenure_in_months=TENURE_IN_MONTHS)
def test_emi_strategy_same_inputs_twice_gives_equal_schedules(
    strategy: EmiCalculationStrategy, principal_in_paise: int, tenure_in_months: int
) -> None:
    """Calculation is deterministic: repeating it with the same inputs gives an equal schedule."""
    first_schedule = calculate_or_none(strategy, principal_in_paise, tenure_in_months)
    second_schedule = calculate_or_none(strategy, principal_in_paise, tenure_in_months)

    assert first_schedule == second_schedule
