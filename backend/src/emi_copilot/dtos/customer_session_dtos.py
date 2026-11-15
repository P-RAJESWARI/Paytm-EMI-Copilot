"""Wire schemas of POST /api/v1/customer-sessions: the QR token in, the session for C1 out."""

from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from emi_copilot.dtos.comfort_check_dtos import ComfortCheckStatus, describe_comfort_check_answer
from emi_copilot.dtos.wire_types import (
    VISIBLE_ASCII_PATTERN,
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    PositiveAmountInPaise,
)
from emi_copilot.services.customer.customer_session_types import (
    CustomerSessionSummary,
    StartedCustomerSession,
)

EXAMPLE_CUSTOMER_SESSION_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0E"
MAXIMUM_QR_TOKEN_LENGTH = 512
"""A signed QR token is about 170 characters (ADR 0015); the cap only bounds the input."""


class StartCustomerSessionRequest(CamelCaseRequestBodyModel):
    """The token read from the QR the merchant shows; it is never logged."""

    qr_token: Annotated[
        str,
        StringConstraints(
            min_length=1, max_length=MAXIMUM_QR_TOKEN_LENGTH, pattern=VISIBLE_ASCII_PATTERN
        ),
        Field(
            description="The token after #t= in the QR link, sent as is.", examples=["<qr-token>"]
        ),
    ]


class CustomerSessionResponse(CamelCaseResponseModel):
    """The session opened by the QR: send sessionToken as X-Customer-Session-Token from now on."""

    customer_session_id: Annotated[str, Field(examples=[EXAMPLE_CUSTOMER_SESSION_ID])]
    session_token: Annotated[str, Field(examples=["<session-token>"])]
    session_code: Annotated[str, Field(examples=["4821"])]
    shop_name: Annotated[str, Field(examples=["Ravi Electronics"])]
    product_name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    expires_at: Annotated[datetime, Field(examples=["2026-11-15T10:00:00Z"])]
    is_voice_available: Annotated[
        bool,
        Field(
            description="Whether to offer the microphone: speech is not switched off.",
            examples=[True],
        ),
    ]

    @classmethod
    def from_started_session(
        cls, started_session: StartedCustomerSession, *, is_voice_available: bool
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
            is_voice_available=is_voice_available,
        )


class CustomerSessionSummaryResponse(CamelCaseResponseModel):
    """The session as C1 shows it and the customer's own progress; the token is never echoed.

    comfortCheckStatus is null until the customer answers the comfort check.
    """

    customer_session_id: Annotated[str, Field(examples=[EXAMPLE_CUSTOMER_SESSION_ID])]
    session_code: Annotated[str, Field(examples=["4821"])]
    shop_name: Annotated[str, Field(examples=["Ravi Electronics"])]
    product_name: Annotated[str, Field(examples=["Example phone, 128 GB"])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    expires_at: Annotated[datetime, Field(examples=["2026-11-15T10:00:00Z"])]
    has_confirmed_budget: Annotated[bool, Field(examples=[True])]
    comfort_check_status: ComfortCheckStatus | None
    has_consented: Annotated[bool, Field(examples=[False])]
    is_voice_available: Annotated[
        bool,
        Field(
            description="Whether to offer the microphone: speech is not switched off.",
            examples=[True],
        ),
    ]

    @classmethod
    def from_summary(
        cls, summary: CustomerSessionSummary, *, is_voice_available: bool
    ) -> "CustomerSessionSummaryResponse":
        """Converts the summary, with the price in integer paise."""
        return cls(
            customer_session_id=summary.customer_session_id,
            session_code=summary.session_code,
            shop_name=summary.shop_name,
            product_name=summary.product_name,
            price_in_paise=summary.price.to_paise(),
            expires_at=summary.expires_at,
            has_confirmed_budget=summary.has_confirmed_budget,
            comfort_check_status=describe_comfort_check_answer(summary.comfort_check_status),
            has_consented=summary.has_consented,
            is_voice_available=is_voice_available,
        )
