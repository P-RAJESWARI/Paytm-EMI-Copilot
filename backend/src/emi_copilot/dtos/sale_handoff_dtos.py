"""Wire schemas of the M4 hand-off: agreed plan, EDC steps, payment link and payment state.

Rule 6 holds: a merchant sees the sale summary, the plan and totals, the link it shows on the
tablet and where the payment stands; never any customer detail. The privacy contract test pins
the exact property names.
"""

from typing import Annotated

from pydantic import AwareDatetime, Field

from emi_copilot.domain.payments import PaymentAttemptStatus
from emi_copilot.domain.sales import EdcEmiProgramme, EdcInstructions
from emi_copilot.dtos.payment_status_dtos import PublicPaymentStatus, to_public_payment_status
from emi_copilot.dtos.sale_dtos import SaleSummaryResponse, to_wire_moment
from emi_copilot.dtos.wire_types import CamelCaseResponseModel, PositiveAmountInPaise
from emi_copilot.services.payment_handoff_types import PaymentLinkHandoff
from emi_copilot.services.sale_handoff_views import (
    HandoffPaymentStatus,
    LatestPaymentLink,
    SaleHandoffView,
)

MOCK_PAYMENT_URL_EXAMPLE = "https://mock-payments.invalid/pay/mock-link-0123456789abcdef0123"
PAYMENT_URL_DESCRIPTION = (
    "Show it on the tablet as a QR code with a copy button; it is never sent anywhere by us."
)


class EdcInstructionsResponse(CamelCaseResponseModel):
    """What to key into the card machine: the EMI menu, product, tenure and amount to check."""

    emi_programme: EdcEmiProgramme
    product_name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    tenure_in_months: Annotated[int, Field(ge=1, examples=[6])]
    is_no_extra_cost: Annotated[bool, Field(description="True when the customer pays no extra.")]
    amount_in_paise: Annotated[
        PositiveAmountInPaise,
        Field(description="The item price to check on the machine.", examples=[2_200_000]),
    ]

    @classmethod
    def from_instructions(cls, instructions: EdcInstructions) -> "EdcInstructionsResponse":
        """Converts the steps, with the amount in integer paise."""
        return cls(
            emi_programme=instructions.emi_programme,
            product_name=instructions.product_name,
            tenure_in_months=instructions.tenure_in_months,
            is_no_extra_cost=instructions.is_no_extra_cost,
            amount_in_paise=instructions.amount.to_paise(),
        )


class LatestPaymentLinkResponse(CamelCaseResponseModel):
    """The sale's newest payment link and where its payment stands."""

    order_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0A"])]
    payment_url: Annotated[
        str, Field(description=PAYMENT_URL_DESCRIPTION, examples=[MOCK_PAYMENT_URL_EXAMPLE])
    ]
    status: Annotated[PublicPaymentStatus, Field(examples=[PublicPaymentStatus.AWAITING_PAYMENT])]

    @classmethod
    def from_link(cls, link: LatestPaymentLink) -> "LatestPaymentLinkResponse":
        """Converts the link with its public status."""
        return cls(
            order_id=link.order_id,
            payment_url=link.payment_url,
            status=to_public_payment_status(link.status),
        )


class SalePaymentStatusResponse(CamelCaseResponseModel):
    """Where an agreed sale's payment stands; the confirmation time is set only once PAID."""

    payment_status: HandoffPaymentStatus
    payment_confirmed_at: Annotated[
        AwareDatetime | None,
        Field(description="When the gateway's confirmed payment moved the sale to PAID, UTC."),
    ]

    @classmethod
    def from_view(cls, view: SaleHandoffView) -> "SalePaymentStatusResponse":
        """Converts the payment part of a hand-off view."""
        confirmed_at = view.payment_confirmed_at
        return cls(
            payment_status=view.payment_status,
            payment_confirmed_at=None if confirmed_at is None else to_wire_moment(confirmed_at),
        )


class SaleHandoffResponse(SalePaymentStatusResponse):
    """M4: the sale with its agreed plan (monthly, extra and total), EDC steps and latest link."""

    sale: SaleSummaryResponse
    edc_instructions: EdcInstructionsResponse
    latest_payment_link: LatestPaymentLinkResponse | None

    @classmethod
    def from_handoff_view(cls, view: SaleHandoffView) -> "SaleHandoffResponse":
        """Converts the whole hand-off view."""
        link = view.latest_payment_link
        return cls.model_validate(
            {
                **SalePaymentStatusResponse.from_view(view).model_dump(),
                "sale": SaleSummaryResponse.from_counter_sale(view.counter_sale),
                "edc_instructions": EdcInstructionsResponse.from_instructions(
                    view.edc_instructions
                ),
                "latest_payment_link": (
                    None if link is None else LatestPaymentLinkResponse.from_link(link)
                ),
            }
        )


class SalePaymentLinkResponse(CamelCaseResponseModel):
    """The link made for the agreed plan; a replay of its Idempotency-Key gives the same body.

    status is the status the link had when made (AWAITING_PAYMENT), so a replay is identical;
    the current status is served by GET /api/v1/sales/{saleId}/payment-status.
    """

    order_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0A"])]
    payment_url: Annotated[
        str, Field(description=PAYMENT_URL_DESCRIPTION, examples=[MOCK_PAYMENT_URL_EXAMPLE])
    ]
    amount_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    status: Annotated[PublicPaymentStatus, Field(examples=[PublicPaymentStatus.AWAITING_PAYMENT])]

    @classmethod
    def from_handoff(cls, handoff: PaymentLinkHandoff) -> "SalePaymentLinkResponse":
        """Converts a new or replayed hand-off into the same body."""
        return cls(
            order_id=handoff.order_id,
            payment_url=handoff.payment_url,
            amount_in_paise=handoff.amount.to_paise(),
            status=to_public_payment_status(PaymentAttemptStatus.LINK_CREATED),
        )
