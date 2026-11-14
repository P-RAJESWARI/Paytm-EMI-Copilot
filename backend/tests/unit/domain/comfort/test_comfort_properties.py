"""Property-based tests for the comfort ratio and bands over realistic amounts.

Ranges: monthly commitment ₹0 to ₹10,00,000 and monthly inflow ₹0.01 to ₹10,00,000, in whole
paise. Basis points are checked against an independent integer oracle in paise.
"""

from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.domain.comfort import ComfortBand, ComfortBandClassificationStrategy, ComfortRatio
from emi_copilot.domain.money import Money

COMMITMENT_IN_PAISE = st.integers(min_value=0, max_value=100_000_000)
INFLOW_IN_PAISE = st.integers(min_value=1, max_value=100_000_000)
BAND_ORDER = (ComfortBand.COMFORTABLE, ComfortBand.STRETCHING, ComfortBand.RISKY)
CLASSIFICATION_STRATEGY = ComfortBandClassificationStrategy()


def reference_basis_points(commitment_in_paise: int, inflow_in_paise: int) -> int:
    """Rounds commitment / inflow x 10,000 half-up using integers only."""
    return (2 * commitment_in_paise * 10_000 + inflow_in_paise) // (2 * inflow_in_paise)


def build_ratio(commitment_in_paise: int, inflow_in_paise: int) -> ComfortRatio:
    """Builds a ratio from two paise amounts."""
    return ComfortRatio(Money.from_paise(commitment_in_paise), Money.from_paise(inflow_in_paise))


@given(commitment_in_paise=COMMITMENT_IN_PAISE, inflow_in_paise=INFLOW_IN_PAISE)
def test_comfort_ratio_any_amounts_matches_integer_reference(
    commitment_in_paise: int, inflow_in_paise: int
) -> None:
    """Basis points equal the half-up integer reference for every pair of amounts."""
    ratio = build_ratio(commitment_in_paise, inflow_in_paise)
    assert ratio.in_basis_points == reference_basis_points(commitment_in_paise, inflow_in_paise)


@given(
    first_commitment_in_paise=COMMITMENT_IN_PAISE,
    second_commitment_in_paise=COMMITMENT_IN_PAISE,
    inflow_in_paise=INFLOW_IN_PAISE,
)
def test_comfort_ratio_larger_commitment_never_gives_a_lower_ratio_or_band(
    first_commitment_in_paise: int, second_commitment_in_paise: int, inflow_in_paise: int
) -> None:
    """Paying more each month never makes the ratio smaller or the band more comfortable."""
    smaller_in_paise, larger_in_paise = sorted(
        (first_commitment_in_paise, second_commitment_in_paise)
    )
    smaller_ratio = build_ratio(smaller_in_paise, inflow_in_paise)
    larger_ratio = build_ratio(larger_in_paise, inflow_in_paise)
    assert smaller_ratio.in_basis_points <= larger_ratio.in_basis_points
    smaller_band = CLASSIFICATION_STRATEGY.classify(smaller_ratio)
    larger_band = CLASSIFICATION_STRATEGY.classify(larger_ratio)
    assert BAND_ORDER.index(smaller_band) <= BAND_ORDER.index(larger_band)


@given(commitment_in_paise=COMMITMENT_IN_PAISE, inflow_in_paise=INFLOW_IN_PAISE)
def test_comfort_band_same_inputs_twice_gives_the_same_band(
    commitment_in_paise: int, inflow_in_paise: int
) -> None:
    """Classification is deterministic: equal ratios always get the same band."""
    first_band = CLASSIFICATION_STRATEGY.classify(build_ratio(commitment_in_paise, inflow_in_paise))
    second_band = CLASSIFICATION_STRATEGY.classify(
        build_ratio(commitment_in_paise, inflow_in_paise)
    )
    assert first_band is second_band
