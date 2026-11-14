"""The five steps of the merchant's sales funnel (M5), counted per sale and never per person."""

from enum import StrEnum


class FunnelStage(StrEnum):
    """A step a sale reached; stored by value, so a rename needs a migration.

    The merchant sees only counts per stage, never which sale or customer reached which step
    (rule 6). In Layer 2 live code records STARTED, AGREED and PAID; BUDGET_TOLD and PLANS_VIEWED
    come from the Layer 3 customer flow and from the step 2.4 demo seed.
    """

    STARTED = "STARTED"
    """The merchant started the sale ("Started")."""

    BUDGET_TOLD = "BUDGET_TOLD"
    """The customer confirmed a monthly budget ("Told a budget")."""

    PLANS_VIEWED = "PLANS_VIEWED"
    """The customer saw the plan comparison ("Saw the plans")."""

    AGREED = "AGREED"
    """The customer agreed to a plan ("Agreed to a plan")."""

    PAID = "PAID"
    """The gateway confirmed the payment ("Paid")."""
