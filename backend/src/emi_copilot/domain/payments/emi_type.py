"""How an EMI plan is priced for the customer, in our own words rather than a vendor's."""

from enum import StrEnum


class EmiType(StrEnum):
    """The pricing kind of an EMI plan; stored by value inside frozen offer snapshots."""

    NO_COST = "NO_COST"
    """Someone else (for example the brand) pays the interest, so the customer pays no extra."""

    STANDARD = "STANDARD"
    """The customer pays the lender's extra cost on top of the price."""
