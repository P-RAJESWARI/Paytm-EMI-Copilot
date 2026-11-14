"""Tests for ComfortThresholds and the demo heuristics it holds."""

import pytest

from emi_copilot.domain.comfort import DEMO_COMFORT_THRESHOLDS, ComfortThresholds
from emi_copilot.domain.errors import InvalidComfortInputError


def test_demo_comfort_thresholds_are_thirty_five_and_fifty_percent() -> None:
    """security-and-compliance.md section 6: Stretching from 35%, Risky above 50%."""
    assert DEMO_COMFORT_THRESHOLDS.stretching_from_in_basis_points == 3500
    assert DEMO_COMFORT_THRESHOLDS.risky_above_in_basis_points == 5000


def test_comfort_thresholds_equal_values_are_accepted() -> None:
    """Equal thresholds leave Stretching as a single basis point, which is still a valid rule."""
    thresholds = ComfortThresholds(4000, 4000)
    assert thresholds.risky_above_in_basis_points == 4000


@pytest.mark.parametrize(
    ("stretching_from", "risky_above", "expected_message"),
    [
        (5000, 3500, "cannot be above"),
        (0, 5000, "above zero"),
        (-1, 5000, "above zero"),
        (True, 5000, "whole number"),
        (3500, False, "whole number"),
        ("3500", 5000, "whole number"),
        (3500, 5000.0, "whole number"),
    ],
)
def test_comfort_thresholds_with_invalid_values_raise(
    stretching_from: object, risky_above: object, expected_message: str
) -> None:
    """Inverted, non-positive, bool, text or float thresholds are refused."""
    with pytest.raises(InvalidComfortInputError, match=expected_message):
        ComfortThresholds(stretching_from, risky_above)  # type: ignore[arg-type]


def test_invalid_comfort_input_error_has_a_stable_code() -> None:
    """The API maps the error to problem+json by this code."""
    assert InvalidComfortInputError.code == "INVALID_COMFORT_INPUT"
