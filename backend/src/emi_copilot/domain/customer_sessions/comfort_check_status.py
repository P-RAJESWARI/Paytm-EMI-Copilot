"""ComfortCheckStatus: whether the customer was asked about, ran or skipped the comfort check."""

from enum import StrEnum


class ComfortCheckStatus(StrEnum):
    """The customer's comfort check choice (C3); stored by value, so a rename needs a migration.

    Skipping is always allowed; the plans are then shown without bands (DESIGN_SPEC section 7).
    """

    NOT_ASKED = "NOT_ASKED"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
