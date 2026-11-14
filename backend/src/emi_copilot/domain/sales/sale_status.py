"""Where a sale at the counter stands; the only sale progress a merchant ever sees (rule 6)."""

from enum import StrEnum


class SaleStatus(StrEnum):
    """The five merchant-visible sale statuses; stored by value, so a rename needs a migration.

    None of them reveals a customer's step-by-step progress: CHOOSING covers everything from the
    QR scan to the moment the customer agrees to a plan.
    """

    CHOOSING = "CHOOSING"
    """The customer is choosing a plan on their phone (or has not opened the QR yet)."""

    READY_TO_PAY = "READY_TO_PAY"
    """The customer agreed to a plan; the merchant can take the payment on the gateway."""

    PAID = "PAID"
    """The gateway confirmed the payment server-side. Final."""

    PAYMENT_NOT_COMPLETED = "PAYMENT_NOT_COMPLETED"
    """The gateway reported the payment did not go through; the merchant may try again."""

    EXPIRED = "EXPIRED"
    """The customer did not agree to a plan in time; the sale left the counter list."""


OPEN_SALE_STATUSES = frozenset(
    {SaleStatus.CHOOSING, SaleStatus.READY_TO_PAY, SaleStatus.PAYMENT_NOT_COMPLETED}
)
"""Sales still in play at the counter; their session codes must differ within one shop."""

STATUSES_WITH_CHOSEN_PLAN = frozenset(
    {SaleStatus.READY_TO_PAY, SaleStatus.PAID, SaleStatus.PAYMENT_NOT_COMPLETED}
)
"""Every status reached only after the customer agreed to a plan, so a plan is always stored."""
