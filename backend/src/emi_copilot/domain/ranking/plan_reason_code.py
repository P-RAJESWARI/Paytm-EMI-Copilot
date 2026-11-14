"""Factual reasons attached to a ranked plan; none of them ranks a plan as better for a customer."""

from enum import StrEnum


class PlanReasonCode(StrEnum):
    """A fact about a plan that the frontend turns into translated text (ADR 0020 decision 5).

    Declaration order is the order codes are listed on a plan. There is deliberately no code that
    recommends a plan (CLAUDE.md section 2, rule 7).
    """

    WITHIN_BUDGET = "WITHIN_BUDGET"
    """The plan's monthly commitment is at or below the customer's monthly budget."""

    ABOVE_BUDGET = "ABOVE_BUDGET"
    """The plan's monthly commitment is above the customer's monthly budget."""

    NO_EXTRA_COST = "NO_EXTRA_COST"
    """The customer pays nothing on top of the price."""

    LOWEST_MONTHLY_AMOUNT = "LOWEST_MONTHLY_AMOUNT"
    """No plan in the list has a smaller monthly commitment; ties all carry it."""

    LOWEST_EXTRA_IN_TOTAL = "LOWEST_EXTRA_IN_TOTAL"
    """No plan in the list has a smaller extra in total; ties all carry it."""
