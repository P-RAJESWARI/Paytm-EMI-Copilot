"""What the sale hand-off returns: agreed plan, EDC steps, latest link and payment state."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from emi_copilot.domain.errors import IllegalSaleTransitionError
from emi_copilot.domain.payments import PaymentAttempt, PaymentAttemptStatus
from emi_copilot.domain.sales import ChosenPlan, EdcInstructions, Sale, SaleStatus
from emi_copilot.services.sale_views import CounterSale


class HandoffPaymentStatus(StrEnum):
    """Where an agreed sale's payment stands, as M4 shows it; never "declined" (spec 7.5)."""

    WAITING = "WAITING"
    """The customer agreed; no confirmed payment yet."""

    PAID = "PAID"
    """The gateway confirmed the payment server-side."""

    NOT_COMPLETED = "NOT_COMPLETED"
    """The gateway reported that the payment did not go through; a new link may be made."""


HANDOFF_PAYMENT_STATUS_BY_SALE_STATUS: Mapping[SaleStatus, HandoffPaymentStatus] = MappingProxyType(
    {
        SaleStatus.READY_TO_PAY: HandoffPaymentStatus.WAITING,
        SaleStatus.PAID: HandoffPaymentStatus.PAID,
        SaleStatus.PAYMENT_NOT_COMPLETED: HandoffPaymentStatus.NOT_COMPLETED,
    }
)
"""The statuses that have an agreed plan; CHOOSING and EXPIRED have no hand-off at all."""


@dataclass(frozen=True, slots=True)
class LatestPaymentLink:
    """The sale's newest payment link, shown on the tablet as a QR code and a copy button.

    The URL is shown, never sent anywhere or logged (plan Q6), so it is kept out of repr.
    """

    order_id: str
    payment_url: str = field(repr=False)
    status: PaymentAttemptStatus


@dataclass(frozen=True, slots=True)
class SaleHandoffView:
    """An agreed sale as M4 shows it; payment_confirmed_at is set only once it is PAID."""

    counter_sale: CounterSale
    edc_instructions: EdcInstructions
    latest_payment_link: LatestPaymentLink | None
    payment_status: HandoffPaymentStatus
    payment_confirmed_at: datetime | None


def require_agreed_plan(sale: Sale) -> ChosenPlan:
    """Gives the sale's agreed plan, or raises SALE_STATE_CONFLICT while CHOOSING or EXPIRED."""
    if sale.chosen_plan is None:
        raise IllegalSaleTransitionError(
            f"A sale that is {sale.status.value} has no agreed plan to hand off."
        )
    return sale.chosen_plan


def build_latest_payment_link(latest_attempt: PaymentAttempt | None) -> LatestPaymentLink | None:
    """Gives the newest attempt's link, or None when it has none (yet, or ever)."""
    if latest_attempt is None or latest_attempt.payment_link_url is None:
        return None
    return LatestPaymentLink(
        order_id=latest_attempt.order_id,
        payment_url=latest_attempt.payment_link_url,
        status=latest_attempt.status,
    )


def build_sale_handoff_view(
    counter_sale: CounterSale, latest_attempt: PaymentAttempt | None
) -> SaleHandoffView:
    """Assembles M4's view of an agreed sale from the sale and its newest payment attempt."""
    sale = counter_sale.sale
    chosen_plan = require_agreed_plan(sale)
    payment_status = HANDOFF_PAYMENT_STATUS_BY_SALE_STATUS[sale.status]
    return SaleHandoffView(
        counter_sale=counter_sale,
        edc_instructions=EdcInstructions.for_chosen_plan(chosen_plan, counter_sale.product_name),
        latest_payment_link=build_latest_payment_link(latest_attempt),
        payment_status=payment_status,
        payment_confirmed_at=(
            sale.status_changed_at if payment_status is HandoffPaymentStatus.PAID else None
        ),
    )
