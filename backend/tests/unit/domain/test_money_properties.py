"""Property-based tests for Money: exact arithmetic and half-up rounding hold for any amount."""

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.domain.money import Money

# Every amount a signed 64-bit BigInteger paise column can hold.
WIDE_PAISE_RANGE = st.integers(min_value=0, max_value=2**63 - 1)
# Rupee amounts with up to six decimal places, as produced by intermediate EMI maths.
SUB_PAISE_MONEY = st.integers(min_value=0, max_value=10**15).map(
    lambda micro_rupees: Money.from_rupees(Decimal(micro_rupees).scaleb(-6))
)


@given(amount_in_paise=WIDE_PAISE_RANGE)
def test_money_from_paise_to_paise_round_trips_any_amount(amount_in_paise: int) -> None:
    """Paise survive the trip into the domain and back unchanged."""
    assert Money.from_paise(amount_in_paise).to_paise() == amount_in_paise


@given(first=SUB_PAISE_MONEY, second=SUB_PAISE_MONEY)
def test_money_addition_is_commutative(first: Money, second: Money) -> None:
    """Order of addition does not matter."""
    assert first + second == second + first


@given(first=SUB_PAISE_MONEY, second=SUB_PAISE_MONEY, third=SUB_PAISE_MONEY)
def test_money_addition_is_associative(first: Money, second: Money, third: Money) -> None:
    """Grouping of addition does not matter."""
    assert (first + second) + third == first + (second + third)


@given(first=SUB_PAISE_MONEY, second=SUB_PAISE_MONEY)
def test_money_adding_then_subtracting_returns_original(first: Money, second: Money) -> None:
    """Addition and subtraction are exact inverses."""
    assert first + second - second == first


@given(amount=SUB_PAISE_MONEY)
def test_money_rounded_to_paise_is_idempotent(amount: Money) -> None:
    """Rounding an already rounded amount changes nothing."""
    assert amount.rounded_to_paise().rounded_to_paise() == amount.rounded_to_paise()


@given(amount=SUB_PAISE_MONEY)
def test_money_rounded_to_paise_is_always_whole_paise(amount: Money) -> None:
    """The rounded result can always be converted to integer paise."""
    rounded = amount.rounded_to_paise()
    assert rounded.is_whole_paise
    assert isinstance(rounded.to_paise(), int)


@given(amount=SUB_PAISE_MONEY)
def test_money_rounded_to_paise_error_is_at_most_half_a_paisa(amount: Money) -> None:
    """Rounding moves an amount by no more than half a paisa."""
    rounding_error = amount.rounded_to_paise().amount_in_rupees - amount.amount_in_rupees
    assert abs(rounding_error) <= Decimal("0.005")
