"""Wire schemas of the sale endpoints: what a merchant may see of a sale, and nothing more.

Rule 6: a sale is its status (one of five), the product, the price, the agreed plan and the
totals. No customer income, EMIs, ratios, budget or step-by-step progress exists here, and the
privacy contract test pins the exact property names.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, Field

from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales import ChosenPlan, SaleStatus
from emi_copilot.dtos.wire_types import (
    CamelCaseQueryModel,
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    OpaqueIdentifier,
    PositiveAmountInPaise,
)
from emi_copilot.services.sale_views import (
    CounterSale,
    CustomerQrLink,
    StartedSale,
    StartSaleCommand,
)

EXAMPLE_SALE_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0F"
EXAMPLE_PRODUCT_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0D"


def to_wire_moment(moment: datetime) -> datetime:
    """Gives a moment in UTC, rounded down to the second, as every timestamp on the wire is."""
    return moment.astimezone(UTC).replace(microsecond=0)


class SalesView(StrEnum):
    """Which list of sales to read; the counter view is the only one in Layer 2."""

    COUNTER = "counter"
    """Sales started today in the shop's time zone (IST), newest first, without expired ones."""


class StartSaleRequest(CamelCaseRequestBodyModel):
    """The product the customer wants; the price is always the catalogue list price."""

    product_id: Annotated[
        OpaqueIdentifier,
        Field(description="A product id from GET /api/v1/products.", examples=[EXAMPLE_PRODUCT_ID]),
    ]

    def to_command(self, idempotency_key: str | None) -> StartSaleCommand:
        """Gives the service command for this body, under the caller's Idempotency-Key if any."""
        return StartSaleCommand(product_id=self.product_id, idempotency_key=idempotency_key)


class SalesQuery(CamelCaseQueryModel):
    """Which sales list to read."""

    view: Annotated[
        SalesView, Field(description="Only `counter` exists: today's sales at the counter.")
    ]


class ChosenPlanResponse(CamelCaseResponseModel):
    """The plan the customer agreed to, exactly as shown to them (plan Q17, ADR 0001).

    monthlyInstallmentInPaise is the lender's quoted monthly figure; the extra and the total
    come from the exact schedule on the sale price.
    """

    offer_id: Annotated[str, Field(examples=["mock-offer-no-cost-6m"])]
    plan_kind: EmiType
    lender_label: Annotated[str, Field(examples=["Brand"])]
    tenure_in_months: Annotated[int, Field(ge=1, examples=[6])]
    monthly_installment_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[366_667])]
    extra_in_total_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[0])]
    total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]

    @classmethod
    def from_chosen_plan(cls, chosen_plan: ChosenPlan) -> "ChosenPlanResponse":
        """Converts the frozen plan to integer paise for the wire."""
        return cls(
            offer_id=chosen_plan.offer_id,
            plan_kind=chosen_plan.plan_kind,
            lender_label=chosen_plan.lender_label,
            tenure_in_months=chosen_plan.tenure_in_months,
            monthly_installment_in_paise=chosen_plan.monthly_installment.to_paise(),
            extra_in_total_in_paise=chosen_plan.extra_in_total.to_paise(),
            total_payable_in_paise=chosen_plan.total_payable.to_paise(),
        )


class CustomerQrResponse(CamelCaseResponseModel):
    """What the QR code encodes and when it stops working; shown once, never stored."""

    customer_url: Annotated[
        str,
        Field(
            description=(
                "Encode this in the QR code. The token is in the #t= fragment, which a browser "
                "never sends to a server; do not log or store it."
            ),
            examples=["http://localhost:5174/#t=<signed-token>"],
        ),
    ]
    expires_at: Annotated[
        AwareDatetime,
        Field(
            description="When the QR code stops working, UTC.", examples=["2026-11-15T09:45:00Z"]
        ),
    ]

    @classmethod
    def from_link(cls, qr_link: CustomerQrLink) -> "CustomerQrResponse":
        """Converts a freshly issued QR link."""
        return cls(customer_url=qr_link.customer_url, expires_at=to_wire_moment(qr_link.expires_at))


class SaleSummaryResponse(CamelCaseResponseModel):
    """One sale on the counter list: code, product, price, status and, once agreed, the plan."""

    sale_id: Annotated[str, Field(examples=[EXAMPLE_SALE_ID])]
    session_code: Annotated[
        str,
        Field(
            description="Four digits to tell sales apart on screen; never a credential.",
            examples=["4821"],
        ),
    ]
    product_name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    status: SaleStatus
    status_changed_at: Annotated[
        AwareDatetime, Field(description="When the status last changed, UTC.")
    ]
    chosen_plan: ChosenPlanResponse | None

    @classmethod
    def summary_fields(cls, counter_sale: CounterSale) -> dict[str, object]:
        """Gives the summary's fields for a sale, shared with the detail shape."""
        sale = counter_sale.sale
        return {
            "sale_id": sale.id,
            "session_code": sale.session_code.value,
            "product_name": counter_sale.product_name,
            "price_in_paise": sale.price.to_paise(),
            "status": sale.status,
            "status_changed_at": to_wire_moment(sale.status_changed_at),
            "chosen_plan": (
                None
                if sale.chosen_plan is None
                else ChosenPlanResponse.from_chosen_plan(sale.chosen_plan)
            ),
        }

    @classmethod
    def from_counter_sale(cls, counter_sale: CounterSale) -> "SaleSummaryResponse":
        """Converts a sale for the counter list."""
        return cls.model_validate(cls.summary_fields(counter_sale))


class SaleDetailResponse(SaleSummaryResponse):
    """One sale with its product id and start; qr is set only in the answer that issued it."""

    product_id: Annotated[str, Field(examples=[EXAMPLE_PRODUCT_ID])]
    started_at: Annotated[AwareDatetime, Field(description="When the sale started, UTC.")]
    qr: CustomerQrResponse | None

    @classmethod
    def from_counter_sale_and_link(
        cls, counter_sale: CounterSale, qr_link: CustomerQrLink | None
    ) -> "SaleDetailResponse":
        """Converts a sale, with the QR link when one was just issued (raw tokens aren't kept)."""
        return cls.model_validate(
            {
                **cls.summary_fields(counter_sale),
                "product_id": counter_sale.sale.product_id,
                "started_at": to_wire_moment(counter_sale.sale.started_at),
                "qr": None if qr_link is None else CustomerQrResponse.from_link(qr_link),
            }
        )

    @classmethod
    def from_started_sale(cls, started_sale: StartedSale) -> "SaleDetailResponse":
        """Converts a new or replayed start; a replay carries no QR link."""
        return cls.from_counter_sale_and_link(started_sale.counter_sale, started_sale.qr_link)


class CounterSalesResponse(CamelCaseResponseModel):
    """Today's sales at the counter, newest first; another shop's sales never appear."""

    sales: list[SaleSummaryResponse]

    @classmethod
    def from_counter_sales(cls, counter_sales: tuple[CounterSale, ...]) -> "CounterSalesResponse":
        """Converts the listed sales, keeping their order."""
        return cls(
            sales=[
                SaleSummaryResponse.from_counter_sale(counter_sale)
                for counter_sale in counter_sales
            ]
        )
