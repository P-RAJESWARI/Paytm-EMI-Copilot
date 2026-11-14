"""Wire schemas of POST /api/v1/customer-sessions: the QR token in, the session for C1 out."""

from datetime import datetime
from typing import Annotated

from pydantic import Field

from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    OpaqueIdentifier,
    PositiveAmountInPaise,
)
from emi_copilot.services.customer_flow.customer_flow_types import (
    ComfortCheckStatus,
    CustomerSessionSummary,
    StartedCustomerSession,
)


class StartCustomerSessionRequest(CamelCaseRequestBodyModel):
    """The token read from the QR the merchant shows; it is never logged."""

    qr_token: Annotated[OpaqueIdentifier, Field(examples=["stub-qr-4821"])]


class CustomerSessionResponse(CamelCaseResponseModel):
    """The session opened by the QR: send sessionToken as X-Customer-Session-Token from now on."""

    customer_session_id: Annotated[str, Field(examples=["stub-customer-session-4821"])]
    session_token: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0C"])]
    session_code: Annotated[str, Field(examples=["4821"])]
    shop_name: Annotated[str, Field(examples=["Ravi Electronics"])]
    product_name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    expires_at: Annotated[datetime, Field(examples=["2026-11-15T10:00:00Z"])]

    @classmethod
    def from_started_session(
        cls, started_session: StartedCustomerSession
    ) -> "CustomerSessionResponse":
        """Converts the started session, with the price in integer paise."""
        return cls(
            customer_session_id=started_session.customer_session_id,
            session_token=started_session.session_token,
            session_code=started_session.session_code,
            shop_name=started_session.shop_name,
            product_name=started_session.product_name,
            price_in_paise=started_session.price.to_paise(),
            expires_at=started_session.expires_at,
        )


class CustomerSessionSummaryResponse(CamelCaseResponseModel):
    """The session as C1 shows it and the customer's own progress; the token is never echoed.

    comfortCheckStatus is null until the customer answers the comfort check.
    """

    customer_session_id: Annotated[str, Field(examples=["stub-customer-session-4821"])]
    session_code: Annotated[str, Field(examples=["4821"])]
    shop_name: Annotated[str, Field(examples=["Ravi Electronics"])]
    product_name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    expires_at: Annotated[datetime, Field(examples=["2026-11-15T10:00:00Z"])]
    has_confirmed_budget: Annotated[bool, Field(examples=[True])]
    comfort_check_status: ComfortCheckStatus | None
    has_consented: Annotated[bool, Field(examples=[False])]

    @classmethod
    def from_summary(cls, summary: CustomerSessionSummary) -> "CustomerSessionSummaryResponse":
        """Converts the summary, with the price in integer paise."""
        return cls(
            customer_session_id=summary.customer_session_id,
            session_code=summary.session_code,
            shop_name=summary.shop_name,
            product_name=summary.product_name,
            price_in_paise=summary.price.to_paise(),
            expires_at=summary.expires_at,
            has_confirmed_budget=summary.has_confirmed_budget,
            comfort_check_status=summary.comfort_check_status,
            has_consented=summary.has_consented,
        )
