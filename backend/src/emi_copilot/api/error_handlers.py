"""Maps typed domain errors and request errors to RFC 7807 application/problem+json responses.

Error mapping table (one row per DomainError class; a subclass not listed falls back to the
nearest listed ancestor, and a unit test requires every class to be listed):

| Error                                   | Status | Why                                       |
|-----------------------------------------|--------|-------------------------------------------|
| request validation (body, query, path,  | 422    | valid HTTP, invalid fields; fieldErrors   |
|   headers incl. Idempotency-Key)        |        |                                           |
| malformed JSON body                     | 400    | api-conventions.md section 3              |
| OfferNotFoundError                      | 404    | the offer is not quoted for the item      |
| PaymentAttemptNotFoundError             | 404    | no payment has this order id              |
| IdempotencyKeyReusedError               | 422    | same key, different body (ADR 0005)       |
| PaymentLinkOutcomeUnknownError          | 409    | replay of a timed-out create (ADR 0005)   |
| PaymentLinkCreationFailedError          | 409    | replay of a failed create                 |
| PaymentLinkCreationInProgressError      | 409    | replay while the first call still runs    |
| WebhookSignatureInvalidError            | 401    | webhook not signed by the gateway         |
| PaymentGatewayTimeoutError              | 504    | the gateway did not answer in time        |
| PaymentGatewayUnavailableError          | 502    | the gateway could not serve the call      |
| PaymentGatewayRequestRejectedError      | 502    | the gateway refused the call              |
| InvalidPaymentGatewayValueError         | 502    | the gateway's answer was unusable         |
| PaymentGatewayError (base)              | 502    | any other gateway failure                 |
| InvalidPairingCredentialsError          | 401    | unknown shop or wrong PIN (one answer)    |
| MerchantAuthenticationRequiredError     | 401    | missing, unknown, expired, revoked token  |
| PairingTemporarilyLockedError           | 429    | repeated wrong PINs; Retry-After is set   |
| RequestRateLimitedError                 | 429    | too many requests; Retry-After is set     |
| RetryLaterError (base)                  | 429    | any other refusal that ends by itself     |
| ProductNotFoundError                    | 404    | not in the merchant's catalogue (hidden)  |
| InvalidMerchantDataError                | 422    | a merchant record would be incomplete     |
| SaleNotFoundError                       | 404    | not the merchant's sale (hidden)          |
| IllegalSaleTransitionError              | 409    | SALE_STATE_CONFLICT: not in this status   |
| SessionCodesExhaustedError              | 409    | every session code is on an open sale     |
| ChosenPlanNoLongerOfferedError          | 409    | the agreed plan is no longer quoted as is |
| PaymentLinkAlreadyActiveError           | 409    | the sale's latest link may still be paid  |
| InvalidReportingPeriodError             | 422    | not a Monday, or a week still to come     |
| InvalidReportDataError                  | 422    | a report figure would be inconsistent     |
| InvalidSaleDataError                    | 422    | a sale record would be inconsistent       |
| every other DomainError                 | 422    | a business rule refused the request       |
| any unexpected exception                | 500    | unexpected_error_middleware.py            |

The detail is the error's English, developer-facing text, which domain errors keep free of
personal data and vendor payloads (domain/errors.py); it is never logged or traced here.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import HTTPExceptionHandler

from emi_copilot.core.request_context import get_current_correlation_id
from emi_copilot.domain import errors
from emi_copilot.dtos.problem_details_dto import (
    PROBLEM_JSON_MEDIA_TYPE,
    FieldErrorResponse,
    ProblemDetailsResponse,
    build_problem_type_url,
)

error_handler_logger = logging.getLogger(__name__)

REQUEST_VALIDATION_FAILED_CODE = "REQUEST_VALIDATION_FAILED"
MALFORMED_REQUEST_CODE = "MALFORMED_REQUEST"
UNEXPECTED_ERROR_CODE = "INTERNAL_SERVER_ERROR"
_JSON_INVALID_ERROR_TYPE = "json_invalid"
UNAUTHORISED_STATUS = 401


@dataclass(frozen=True, slots=True)
class ProblemMapping:
    """How one error class is answered: its HTTP status and a short English title."""

    status: int
    title: str


PROBLEM_MAPPINGS_BY_ERROR_TYPE: Mapping[type[errors.DomainError], ProblemMapping] = (
    MappingProxyType(
        {
            errors.DomainError: ProblemMapping(422, "Request refused by a business rule"),
            errors.InvalidMoneyAmountError: ProblemMapping(422, "Invalid money amount"),
            errors.InvalidEmiTermsError: ProblemMapping(422, "Invalid EMI terms"),
            errors.EmiScheduleNotRepresentableError: ProblemMapping(
                422, "EMI schedule not representable"
            ),
            errors.InvalidOfferSnapshotError: ProblemMapping(422, "Invalid offer snapshot"),
            errors.InvalidPaymentAttemptError: ProblemMapping(422, "Invalid payment attempt"),
            errors.InvalidAuditEventError: ProblemMapping(422, "Invalid audit event"),
            errors.PaymentAttemptAlreadyExistsError: ProblemMapping(
                422, "Payment attempt already exists"
            ),
            errors.PaymentAttemptNotFoundError: ProblemMapping(404, "Payment not found"),
            errors.InvalidPaymentGatewayValueError: ProblemMapping(
                502, "Unusable payment gateway answer"
            ),
            errors.PaymentGatewayError: ProblemMapping(502, "Payment gateway failed"),
            errors.PaymentGatewayTimeoutError: ProblemMapping(504, "Payment gateway timed out"),
            errors.PaymentGatewayUnavailableError: ProblemMapping(
                502, "Payment gateway unavailable"
            ),
            errors.PaymentGatewayRequestRejectedError: ProblemMapping(
                502, "Payment gateway refused the request"
            ),
            errors.WebhookSignatureInvalidError: ProblemMapping(401, "Webhook rejected"),
            errors.OfferNotFoundError: ProblemMapping(404, "Offer not found"),
            errors.IdempotencyKeyReusedError: ProblemMapping(422, "Idempotency key reused"),
            errors.PaymentLinkOutcomeUnknownError: ProblemMapping(
                409, "Payment link outcome unknown"
            ),
            errors.PaymentLinkCreationFailedError: ProblemMapping(
                409, "Payment link was not created"
            ),
            errors.PaymentLinkCreationInProgressError: ProblemMapping(
                409, "Payment link creation in progress"
            ),
            errors.InvalidMerchantDataError: ProblemMapping(422, "Invalid merchant data"),
            errors.InvalidPairingCredentialsError: ProblemMapping(
                401, "Shop id or PIN not recognised"
            ),
            errors.RetryLaterError: ProblemMapping(429, "Try again later"),
            errors.PairingTemporarilyLockedError: ProblemMapping(429, "Pairing temporarily locked"),
            errors.RequestRateLimitedError: ProblemMapping(429, "Too many requests"),
            errors.MerchantAuthenticationRequiredError: ProblemMapping(
                401, "Merchant sign-in required"
            ),
            errors.ProductNotFoundError: ProblemMapping(404, "Product not found"),
            errors.InvalidSaleDataError: ProblemMapping(422, "Invalid sale data"),
            errors.SaleNotFoundError: ProblemMapping(404, "Sale not found"),
            errors.IllegalSaleTransitionError: ProblemMapping(
                409, "Not possible in the sale's current status"
            ),
            errors.SessionCodesExhaustedError: ProblemMapping(409, "No free session code"),
            errors.ChosenPlanNoLongerOfferedError: ProblemMapping(
                409, "Agreed plan no longer offered"
            ),
            errors.PaymentLinkAlreadyActiveError: ProblemMapping(
                409, "A payment link is still active"
            ),
            errors.InvalidReportingPeriodError: ProblemMapping(422, "Invalid reporting period"),
            errors.InvalidReportDataError: ProblemMapping(422, "Invalid report data"),
        }
    )
)

# Framework-raised HTTP errors (unknown route, wrong method, oversized or unparseable body).
HTTP_ERROR_CODES_BY_STATUS: Mapping[int, str] = MappingProxyType(
    {
        400: MALFORMED_REQUEST_CODE,
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        413: "REQUEST_BODY_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
    }
)
_FALLBACK_HTTP_ERROR_CODE = "HTTP_ERROR"


def find_problem_mapping(error: errors.DomainError) -> ProblemMapping:
    """Gives the mapping of the error's class, or of its nearest mapped ancestor.

    DomainError itself is in the table, so every domain error finds a mapping.
    """
    return next(
        PROBLEM_MAPPINGS_BY_ERROR_TYPE[error_class]
        for error_class in type(error).__mro__
        if error_class in PROBLEM_MAPPINGS_BY_ERROR_TYPE
    )


def build_problem_response(
    problem: ProblemDetailsResponse, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    """Renders a problem as application/problem+json; fieldErrors appears only when set."""
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json", by_alias=True, exclude_unset=True),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
        headers=dict(headers) if headers else None,
    )


def build_problem(
    status: int,
    code: str,
    title: str,
    detail: str,
    field_errors: list[FieldErrorResponse] | None = None,
) -> ProblemDetailsResponse:
    """Builds a problem for the current request, carrying its correlation id."""
    problem_fields: dict[str, Any] = {
        "type": build_problem_type_url(code),
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "correlation_id": get_current_correlation_id(),
    }
    if field_errors is not None:
        problem_fields["field_errors"] = field_errors
    return ProblemDetailsResponse.model_validate(problem_fields)


def describe_field_location(location: Sequence[Any]) -> str:
    """Names a field as on the wire: ("body", "offerId") gives "offerId"; the body alone, "body"."""
    field_path = [str(part) for part in location[1:]]
    return ".".join(field_path) if field_path else str(location[0])


def build_problem_headers(error: errors.DomainError) -> dict[str, str]:
    """Gives the headers an error's answer carries: Retry-After, or the bearer challenge."""
    if isinstance(error, errors.RetryLaterError):
        return {"Retry-After": str(error.retry_after_in_seconds)}
    if isinstance(error, errors.MerchantAuthenticationRequiredError):
        return {"WWW-Authenticate": "Bearer"}
    return {}


def handle_domain_error(_request: Request, error: errors.DomainError) -> JSONResponse:
    """Answers a typed domain error with its mapped status, code, detail and any headers."""
    mapping = find_problem_mapping(error)
    # A refused credential (a forged webhook today) is a security event, so it logs louder.
    log_level = logging.WARNING if mapping.status == UNAUTHORISED_STATUS else logging.INFO
    error_handler_logger.log(
        log_level,
        "request refused",
        extra={"error_code": error.code, "http_status_code": mapping.status},
    )
    return build_problem_response(
        build_problem(mapping.status, error.code, mapping.title, error.detail),
        build_problem_headers(error),
    )


def handle_request_validation_error(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    """Answers invalid input with 422 and one fieldError per field; unparseable JSON is a 400."""
    validation_errors = error.errors()
    if any(item["type"] == _JSON_INVALID_ERROR_TYPE for item in validation_errors):
        return build_problem_response(
            build_problem(
                400, MALFORMED_REQUEST_CODE, "Malformed request", "The body is not valid JSON."
            )
        )
    field_errors = [
        FieldErrorResponse(field=describe_field_location(item["loc"]), message=item["msg"])
        for item in validation_errors
    ]
    return build_problem_response(
        build_problem(
            422,
            REQUEST_VALIDATION_FAILED_CODE,
            "Request validation failed",
            "One or more request fields are missing or invalid; see fieldErrors.",
            field_errors,
        )
    )


def handle_http_exception(_request: Request, error: StarletteHTTPException) -> JSONResponse:
    """Answers a framework HTTP error (for example 404 or 405) as a problem, keeping its headers."""
    code = HTTP_ERROR_CODES_BY_STATUS.get(error.status_code, _FALLBACK_HTTP_ERROR_CODE)
    title = code.replace("_", " ").capitalize()
    problem = build_problem(error.status_code, code, title, str(error.detail))
    return build_problem_response(problem, error.headers)


def register_error_handlers(application: FastAPI) -> None:
    """Installs the problem+json handlers for domain, validation and framework HTTP errors.

    Starlette calls a handler only for exceptions of its registered class, so each narrower
    handler signature is safe to register as a general exception handler.
    """
    application.add_exception_handler(
        errors.DomainError, cast("HTTPExceptionHandler", handle_domain_error)
    )
    application.add_exception_handler(
        RequestValidationError, cast("HTTPExceptionHandler", handle_request_validation_error)
    )
    application.add_exception_handler(
        StarletteHTTPException, cast("HTTPExceptionHandler", handle_http_exception)
    )
