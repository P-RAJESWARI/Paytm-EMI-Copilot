"""Providers of the stub customer flow services and the customer session credentials.

STUB until Phase 3C: they read app.state, which the Phase 3A contract application fills; in 3C
they move into api/dependencies.py (ADR 0012).
"""

from typing import Annotated

from fastapi import Depends, Path, Request, Security
from fastapi.security import APIKeyHeader

from emi_copilot.domain.errors import CustomerSessionTokenInvalidError
from emi_copilot.dtos.wire_types import MAXIMUM_IDENTIFIER_LENGTH, VISIBLE_ASCII_PATTERN
from emi_copilot.services.customer_flow.customer_flow_types import CustomerSessionCredentials
from emi_copilot.services.customer_flow.stub_customer_advice_service import (
    StubCustomerAdviceService,
)
from emi_copilot.services.customer_flow.stub_customer_consent_service import (
    StubCustomerConsentService,
)
from emi_copilot.services.customer_flow.stub_customer_flow_services import (
    StubCustomerFlowServices,
)
from emi_copilot.services.customer_flow.stub_customer_session_service import (
    StubCustomerSessionService,
)

CUSTOMER_SESSION_TOKEN_HEADER = "X-Customer-Session-Token"  # noqa: S105 - a header name
CUSTOMER_SESSION_TOKEN_SCHEME_NAME = "CustomerSessionToken"  # noqa: S105 - a scheme name
# auto_error=False, so a missing header becomes our 401 problem, not FastAPI's plain 403.
customer_session_token_header = APIKeyHeader(
    name=CUSTOMER_SESSION_TOKEN_HEADER,
    scheme_name=CUSTOMER_SESSION_TOKEN_SCHEME_NAME,
    description=(
        "The sessionToken from POST /customer-sessions; short-lived and bound to one session. "
        "Missing, wrong or ended tokens answer 401 CUSTOMER_SESSION_TOKEN_INVALID."
    ),
    auto_error=False,
)


def provide_customer_flow_services(request: Request) -> StubCustomerFlowServices:
    """Gives the stub services the contract application stored on app.state."""
    services: StubCustomerFlowServices = request.app.state.customer_flow_services
    return services


CustomerFlowServicesDependency = Annotated[
    StubCustomerFlowServices, Depends(provide_customer_flow_services)
]


def provide_customer_session_service(
    services: CustomerFlowServicesDependency,
) -> StubCustomerSessionService:
    """Gives the session service (start, budget)."""
    return services.session_service


def provide_customer_advice_service(
    services: CustomerFlowServicesDependency,
) -> StubCustomerAdviceService:
    """Gives the advice service (comfort check, plans, alternatives)."""
    return services.advice_service


def provide_customer_consent_service(
    services: CustomerFlowServicesDependency,
) -> StubCustomerConsentService:
    """Gives the consent service (one-time code, consent, receipt)."""
    return services.consent_service


def provide_customer_session_credentials(
    customer_session_id: Annotated[
        str,
        Path(
            alias="customerSessionId",
            min_length=1,
            max_length=MAXIMUM_IDENTIFIER_LENGTH,
            pattern=VISIBLE_ASCII_PATTERN,
            description="The customerSessionId returned when the QR was scanned.",
            examples=["stub-customer-session-4821"],
        ),
    ],
    session_token: Annotated[str | None, Security(customer_session_token_header)],
) -> CustomerSessionCredentials:
    """Pairs the path's session id with the header's token; a missing token is a 401."""
    if not session_token:
        raise CustomerSessionTokenInvalidError(
            "The session token is missing; open the link from the shop's QR again."
        )
    return CustomerSessionCredentials(customer_session_id, session_token)


CustomerSessionServiceDependency = Annotated[
    StubCustomerSessionService, Depends(provide_customer_session_service)
]
CustomerAdviceServiceDependency = Annotated[
    StubCustomerAdviceService, Depends(provide_customer_advice_service)
]
CustomerConsentServiceDependency = Annotated[
    StubCustomerConsentService, Depends(provide_customer_consent_service)
]
CustomerSessionCredentialsDependency = Annotated[
    CustomerSessionCredentials, Depends(provide_customer_session_credentials)
]
