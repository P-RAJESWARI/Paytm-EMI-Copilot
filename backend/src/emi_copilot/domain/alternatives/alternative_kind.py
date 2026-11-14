"""The kinds of smarter alternative C6 offers beside the chosen plan."""

from enum import StrEnum


class AlternativeKind(StrEnum):
    """How an alternative changes the purchase; values travel on the wire."""

    DOWN_PAYMENT = "DOWN_PAYMENT"
    """The same plan on the price less a down payment paid at the counter."""

    LONGER_TENURE = "LONGER_TENURE"
    """Another quoted plan for the same item that runs for more months."""

    CHEAPER_MODEL = "CHEAPER_MODEL"
    """A plan on a cheaper model of the item from the shop's catalogue."""
