"""Wire schemas of POST /api/v1/payment-links: the chosen plan and the link handed back."""

from typing import Annotated

from pydantic import Field

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType, OfferSnapshot, PaymentAttemptStatus
from emi_copilot.dtos.offer_dtos import SAMPLE_PRICE_IN_PAISE
from emi_copilot.dtos.payment_status_dtos import PublicPaymentStatus, to_public_payment_status
from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    OpaqueIdentifier,
    PositiveAmountInPaise,
)
from emi_copilot.services.payment_handoff_types import (
    CreatePaymentLinkCommand,
    PaymentLinkHandoff,
)

# A key is 8 to 255 visible ASCII characters, for example a UUID or a ULID. 255 is the column
# size (payment_handoff_types.MAXIMUM_IDEMPOTENCY_KEY_LENGTH); 8 refuses trivially guessable keys.
MINIMUM_IDEMPOTENCY_KEY_LENGTH = 8
IDEMPOTENCY_KEY_PATTERN = r"^[!-~]+$"
IDEMPOTENCY_KEY_HEADER_DESCRIPTION = (
    "Required. 8 to 255 visible ASCII characters, no spaces (a UUID or ULID is ideal). The same "
    "key with the same body returns the original 201 response; with a different body it is "
    "refused with 422 IDEMPOTENCY_KEY_REUSED (ADR 0005)."
)


class CreatePaymentLinkRequest(CamelCaseRequestBodyModel):
    """The plan the customer chose for one item; every figure is re-quoted server-side."""

    offer_id: Annotated[OpaqueIdentifier, Field(examples=["mock-offer-card-6m"])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[SAMPLE_PRICE_IN_PAISE])]
    product_id: Annotated[OpaqueIdentifier, Field(examples=["product-tv-43"])]
    brand_id: Annotated[OpaqueIdentifier, Field(examples=["brand-demo"])]
    category_id: Annotated[OpaqueIdentifier, Field(examples=["category-televisions"])]

    def to_command(self, idempotency_key: str) -> CreatePaymentLinkCommand:
        """Gives the service command for this body under the caller's Idempotency-Key."""
        return CreatePaymentLinkCommand(
            idempotency_key=idempotency_key,
            offer_id=self.offer_id,
            price=Money.from_paise(self.price_in_paise),
            product_id=self.product_id,
            brand_id=self.brand_id,
            category_id=self.category_id,
        )


class OfferSnapshotResponse(CamelCaseResponseModel):
    """The exact plan frozen when the link was made: tenure - 1 regular installments, then a last.

    The amounts are our schedule's, so they add up to totalPayableInPaise to the paisa.
    """

    offer_id: Annotated[str, Field(examples=["mock-offer-card-6m"])]
    lender_label: Annotated[str, Field(examples=["Your card's bank"])]
    emi_type: EmiType
    tenure_in_months: Annotated[int, Field(ge=1, examples=[6])]
    regular_installment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[385_000])]
    last_installment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[385_000])]
    extra_in_total_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[110_000])]
    total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_310_000])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[SAMPLE_PRICE_IN_PAISE])]

    @classmethod
    def from_snapshot(cls, snapshot: OfferSnapshot, price: Money) -> "OfferSnapshotResponse":
        """Converts a frozen snapshot and the link amount to integer paise for the wire."""
        return cls(
            offer_id=snapshot.offer_id,
            lender_label=snapshot.lender_label,
            emi_type=snapshot.emi_type,
            tenure_in_months=snapshot.tenure_in_months,
            regular_installment_in_paise=snapshot.regular_installment.to_paise(),
            last_installment_in_paise=snapshot.last_installment.to_paise(),
            extra_in_total_in_paise=snapshot.extra_in_total.to_paise(),
            total_payable_in_paise=snapshot.total_payable.to_paise(),
            price_in_paise=price.to_paise(),
        )


class PaymentLinkResponse(CamelCaseResponseModel):
    """The link to hand to the customer, as created; poll the Location URL for later status.

    status is always the status the link had when it was created (AWAITING_PAYMENT), so a replay
    with the same Idempotency-Key returns exactly the original response (api-conventions.md
    section 5). The current status is served by GET /api/v1/payments/{orderId}/status.
    """

    order_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0A"])]
    payment_url: Annotated[
        str, Field(examples=["https://mock-payments.invalid/pay/mock-link-0123456789abcdef0123"])
    ]
    status: Annotated[PublicPaymentStatus, Field(examples=[PublicPaymentStatus.AWAITING_PAYMENT])]
    offer: OfferSnapshotResponse

    @classmethod
    def from_handoff(cls, handoff: PaymentLinkHandoff) -> "PaymentLinkResponse":
        """Converts a hand-off, new or replayed, into the same response body."""
        return cls(
            order_id=handoff.order_id,
            payment_url=handoff.payment_url,
            status=to_public_payment_status(PaymentAttemptStatus.LINK_CREATED),
            offer=OfferSnapshotResponse.from_snapshot(handoff.offer, handoff.amount),
        )
