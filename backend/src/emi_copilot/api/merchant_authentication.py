"""CurrentMerchant: the FastAPI dependency that signs a merchant request in by bearer token.

Every merchant endpoint declares it, so OpenAPI lists the bearer scheme on exactly those
operations. A missing header, a non-bearer scheme and a bad token all answer 401
MERCHANT_AUTHENTICATION_REQUIRED with WWW-Authenticate: Bearer. The token is never logged.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from emi_copilot.api.merchant_dependencies import AuthenticateMerchantServiceDependency
from emi_copilot.domain.errors import MerchantAuthenticationRequiredError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.services.authenticate_merchant_service import AUTHENTICATION_REQUIRED_DETAIL

MERCHANT_BEARER_SCHEME_NAME = "MerchantBearerToken"

merchant_bearer_scheme = HTTPBearer(
    scheme_name=MERCHANT_BEARER_SCHEME_NAME,
    description=(
        "The accessToken from POST /api/v1/merchants/pairing, sent as "
        "`Authorization: Bearer <token>`. It lasts 12 hours by default; pair again after."
    ),
    auto_error=False,
)


def authenticate_current_merchant(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(merchant_bearer_scheme)],
    authenticate_merchant_service: AuthenticateMerchantServiceDependency,
) -> MerchantPrincipal:
    """Gives the merchant the bearer token signs in, or raises the 401 authentication error."""
    if credentials is None:
        raise MerchantAuthenticationRequiredError(AUTHENTICATION_REQUIRED_DETAIL)
    return authenticate_merchant_service.authenticate(credentials.credentials)


CurrentMerchant = Annotated[MerchantPrincipal, Depends(authenticate_current_merchant)]
"""The signed-in merchant; declare it on every merchant endpoint."""
