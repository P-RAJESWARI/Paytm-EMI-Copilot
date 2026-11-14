"""The three comfort bands a plan can fall in; advice for the customer, never a credit decision."""

from enum import StrEnum


class ComfortBand(StrEnum):
    """How a plan's monthly amount sits against the customer's monthly inflow (ADR 0020).

    There are exactly three bands (CLAUDE.md section 2, rule 5). Values travel on the wire and are
    mapped to translated words with an icon by the frontend; colour is never the only signal.
    """

    COMFORTABLE = "COMFORTABLE"
    """All monthly EMIs together take less than the stretching threshold of the inflow."""

    STRETCHING = "STRETCHING"
    """All monthly EMIs together take between the two thresholds of the inflow, both included."""

    RISKY = "RISKY"
    """All monthly EMIs together take more than the risky threshold of the inflow."""
