"""OpenAPI helpers: documented problem responses per endpoint and the exported schema shape."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from emi_copilot.dtos.problem_details_dto import (
    PROBLEM_JSON_MEDIA_TYPE,
    ProblemDetailsResponse,
    build_problem_type_url,
)

JSON_MEDIA_TYPE = "application/json"
EXAMPLE_CORRELATION_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0B"
UNAUTHENTICATED_NOTE = (
    "Layer 1 gateway endpoint: unauthenticated (ADR 0009); it reads public offer terms only. "
    "Money is integer paise; errors are application/problem+json."
)
PAYMENT_MERCHANT_BEARER_NOTE = (
    "Layer 1 gateway endpoint that needs the merchant bearer token since Layer 2 (plan Q16) and "
    "is limited per shop (429 with Retry-After). Money is integer paise; errors are "
    "application/problem+json."
)
MERCHANT_BEARER_NOTE = (
    "Merchant endpoint: send the device's bearer token from POST /api/v1/merchants/pairing. "
    "Only the signed-in shop's own data is returned. Money is integer paise; errors are "
    "application/problem+json."
)
TOO_MANY_REQUESTS_STATUS = 429
_RETRY_AFTER_HEADER = {
    "Retry-After": {
        "description": "Whole seconds to wait before trying again.",
        "schema": {"type": "integer", "minimum": 1},
    }
}
_PROBLEM_SCHEMA_REFERENCE = "#/components/schemas/" + ProblemDetailsResponse.__name__
_OPENAPI_DESCRIPTION = (
    "REST contract for the merchant and customer apps. JSON is camelCase, money is integer "
    "paise (never a float) and every error is an RFC 7807 problem with a stable code."
)


@dataclass(frozen=True, slots=True)
class ProblemExample:
    """One documented error answer: status, stable code, title, detail and when it happens."""

    status: int
    code: str
    title: str
    detail: str
    description: str

    def to_example_body(self) -> dict[str, object]:
        """Gives the problem body this error is answered with, as a documentation example."""
        example_body: dict[str, object] = {
            "type": build_problem_type_url(self.code),
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "code": self.code,
            "correlationId": EXAMPLE_CORRELATION_ID,
        }
        if self.code == "REQUEST_VALIDATION_FAILED":
            example_body["fieldErrors"] = [
                {"field": "priceInPaise", "message": "Input should be greater than 0"}
            ]
        return example_body


def describe_problem_responses(*problem_examples: ProblemExample) -> dict[int | str, Any]:
    """Builds the FastAPI `responses` entry for the given errors, grouped by status code.

    Every operation also documents the generic 500 problem, which any request can meet, and a
    429 answer documents its Retry-After header.
    """
    examples_by_status: dict[int, list[ProblemExample]] = defaultdict(list)
    for problem_example in (*problem_examples, UNEXPECTED_ERROR_PROBLEM):
        examples_by_status[problem_example.status].append(problem_example)
    return {
        status: _describe_problem_status(status, examples)
        for status, examples in sorted(examples_by_status.items())
    }


def _describe_problem_status(status: int, examples: list[ProblemExample]) -> dict[str, Any]:
    """Builds one status entry: the problem model, its joined description and its examples."""
    response: dict[str, Any] = {
        "model": ProblemDetailsResponse,
        "description": " ".join(example.description for example in examples if example.description),
        "content": {
            PROBLEM_JSON_MEDIA_TYPE: {
                "examples": {
                    example.code: {"summary": example.title, "value": example.to_example_body()}
                    for example in examples
                }
            }
        },
    }
    if status == TOO_MANY_REQUESTS_STATUS:
        response["headers"] = _RETRY_AFTER_HEADER
    return response


def move_problem_schemas_to_problem_media_type(openapi_schema: dict[str, Any]) -> None:
    """Serves every problem schema under application/problem+json only, as the API answers it.

    FastAPI places a response model under application/json; problems are never sent as that.
    """
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            for response in operation.get("responses", {}).values():
                content = response.get("content", {})
                json_content = content.get(JSON_MEDIA_TYPE, {})
                if json_content.get("schema", {}).get("$ref") == _PROBLEM_SCHEMA_REFERENCE:
                    del content[JSON_MEDIA_TYPE]
                    content.setdefault(PROBLEM_JSON_MEDIA_TYPE, {})["schema"] = {
                        "$ref": _PROBLEM_SCHEMA_REFERENCE
                    }


def install_openapi_schema(application: FastAPI) -> None:
    """Replaces the application's OpenAPI builder with one that applies the problem media type."""

    def build_openapi_schema() -> dict[str, Any]:
        """Builds the schema once, then serves the cached copy."""
        if application.openapi_schema is None:
            openapi_schema = get_openapi(
                title=application.title,
                version=application.version,
                description=_OPENAPI_DESCRIPTION,
                routes=application.routes,
            )
            move_problem_schemas_to_problem_media_type(openapi_schema)
            application.openapi_schema = openapi_schema
        return application.openapi_schema

    openapi_builder: Callable[[], dict[str, Any]] = build_openapi_schema
    application.openapi = openapi_builder  # type: ignore[method-assign]


UNEXPECTED_ERROR_PROBLEM = ProblemExample(
    500,
    "INTERNAL_SERVER_ERROR",
    "Internal server error",
    "An unexpected error occurred; quote the correlation id when reporting it.",
    "An unexpected failure; the body never holds a stack trace.",
)
REQUEST_VALIDATION_PROBLEM = ProblemExample(
    422,
    "REQUEST_VALIDATION_FAILED",
    "Request validation failed",
    "One or more request fields are missing or invalid; see fieldErrors.",
    "A field, query parameter or header is missing or invalid; fieldErrors names each one.",
)
MALFORMED_REQUEST_PROBLEM = ProblemExample(
    400,
    "MALFORMED_REQUEST",
    "Malformed request",
    "The body is not valid JSON.",
    "The body cannot be parsed.",
)
GATEWAY_TIMEOUT_PROBLEM = ProblemExample(
    504,
    "PAYMENT_GATEWAY_TIMEOUT",
    "Payment gateway timed out",
    "The gateway did not answer in time.",
    "The payment gateway did not answer in time.",
)
GATEWAY_FAILURE_PROBLEMS = (
    ProblemExample(
        502,
        "PAYMENT_GATEWAY_UNAVAILABLE",
        "Payment gateway unavailable",
        "The gateway could not serve the call.",
        "The payment gateway is unavailable, refused the call or answered unusably.",
    ),
    ProblemExample(
        502,
        "PAYMENT_GATEWAY_REQUEST_REJECTED",
        "Payment gateway refused the request",
        "The gateway refused the request as invalid.",
        "",
    ),
    ProblemExample(
        502,
        "INVALID_PAYMENT_GATEWAY_VALUE",
        "Unusable payment gateway answer",
        "The gateway quoted two plans with the same id.",
        "",
    ),
)
MERCHANT_PAYMENT_RATE_LIMITED_PROBLEM = ProblemExample(
    429,
    "RATE_LIMITED",
    "Too many requests",
    "Too many payment requests from this shop; try again after Retry-After.",
    "The shop made too many payment link or status calls in this minute.",
)
MERCHANT_AUTHENTICATION_PROBLEM = ProblemExample(
    401,
    "MERCHANT_AUTHENTICATION_REQUIRED",
    "Merchant sign-in required",
    "A valid merchant bearer token is required; pair the device again.",
    "The bearer token is missing, unknown, expired or revoked; the answer carries "
    "WWW-Authenticate: Bearer. Pair the device again.",
)
