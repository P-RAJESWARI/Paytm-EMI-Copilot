"""TeachBackResult: whether the customer's own words matched the plan's terms closely enough."""

from enum import StrEnum


class TeachBackResult(StrEnum):
    """Advisory only: TRY_AGAIN never blocks consent, it offers to explain the plan again."""

    CLOSE_ENOUGH = "CLOSE_ENOUGH"
    TRY_AGAIN = "TRY_AGAIN"
