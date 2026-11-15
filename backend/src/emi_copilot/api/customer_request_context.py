"""What every customer request carries: the session credentials and the customer's language.

The session id comes from the path and the token from X-Customer-Session-Token; the language
comes from Accept-Language, read leniently because browsers send their own lists.
"""

from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import Depends, Header, Path, Security
from fastapi.security import APIKeyHeader

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import CustomerSessionTokenInvalidError
from emi_copilot.dtos.wire_types import MAXIMUM_IDENTIFIER_LENGTH, VISIBLE_ASCII_PATTERN
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials

CUSTOMER_SESSION_TOKEN_HEADER = "X-Customer-Session-Token"  # noqa: S105 - a header name
CUSTOMER_SESSION_TOKEN_SCHEME_NAME = "CustomerSessionToken"  # noqa: S105 - a scheme name
MAXIMUM_ACCEPT_LANGUAGE_LENGTH = 256
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


def provide_customer_session_credentials(
    customer_session_id: Annotated[
        str,
        Path(
            alias="customerSessionId",
            min_length=1,
            max_length=MAXIMUM_IDENTIFIER_LENGTH,
            pattern=VISIBLE_ASCII_PATTERN,
            description="The customerSessionId returned when the QR was exchanged.",
            examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0E"],
        ),
    ],
    session_token: Annotated[str | None, Security(customer_session_token_header)],
) -> CustomerSessionCredentials:
    """Pairs the path's session id with the header's token; a missing token is a 401."""
    if not session_token:
        raise CustomerSessionTokenInvalidError(
            "The session token is missing; ask the shop for a new QR."
        )
    return CustomerSessionCredentials(customer_session_id, session_token)


def read_language_quality(parameters: str) -> Decimal:
    """Gives an Accept-Language entry's q-value (1 when absent, 0 when unreadable or not finite)."""
    for parameter in parameters.split(";"):
        name, _, value = parameter.strip().partition("=")
        if name.strip().lower() == "q":
            try:
                quality = Decimal(value.strip())
            except InvalidOperation:
                return Decimal(0)
            return quality if quality.is_finite() else Decimal(0)
    return Decimal(1)


def choose_customer_language(accept_language: str | None) -> CustomerLanguage:
    """Gives en or ta, whichever the header prefers (by q-value, then order); English otherwise.

    Browsers send lists such as "ta-IN,ta;q=0.9,en;q=0.8", so the header is read leniently.
    """
    supported_languages = {language.value: language for language in CustomerLanguage}
    ranked_languages = []
    for position, entry in enumerate((accept_language or "").split(",")):
        tag, _, parameters = entry.partition(";")
        primary_subtag = tag.strip().split("-", maxsplit=1)[0].lower()
        quality = read_language_quality(parameters)
        if primary_subtag in supported_languages and quality > 0:
            ranked_languages.append((-quality, position, supported_languages[primary_subtag]))
    return min(ranked_languages)[2] if ranked_languages else CustomerLanguage.ENGLISH


def provide_customer_language(
    accept_language: Annotated[
        str | None,
        Header(
            alias="Accept-Language",
            max_length=MAXIMUM_ACCEPT_LANGUAGE_LENGTH,
            description=(
                "en or ta, the language the customer chose on C1; a browser list such as "
                "ta-IN,ta;q=0.9 also works. Anything else, or no header, means English."
            ),
            examples=["ta"],
        ),
    ] = None,
) -> CustomerLanguage:
    """Gives the customer's language from Accept-Language (English by default)."""
    return choose_customer_language(accept_language)


CustomerSessionCredentialsDependency = Annotated[
    CustomerSessionCredentials, Depends(provide_customer_session_credentials)
]
CustomerLanguageDependency = Annotated[CustomerLanguage, Depends(provide_customer_language)]
