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
from emi_copilot.services.customer_flow.customer_flow_types import StartedCustomerSession


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
