"""The committed OpenAPI document is current, valid and keeps the money and privacy rules."""

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from openapi_spec_validator import validate

from emi_copilot.api.openapi_export import build_openapi_document, render_openapi_document
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.main import create_application

COMMITTED_OPENAPI_PATH = Path(__file__).resolve().parents[3] / "openapi.json"
HTTP_METHODS = frozenset({"get", "put", "post", "delete", "patch", "head", "options"})
CARD_LIKE_WORDS = frozenset({"card", "cvv", "expiry", "pan", "bin"})
CAMEL_CASE_HUMP = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
# Offer discovery (ADR 0009), the signed gateway webhook and pairing itself need no merchant
# bearer token; payment links and payment status do since Layer 2 (plan Q16).
UNAUTHENTICATED_PATH_PREFIXES = (
    "/api/v1/offers",
    "/api/v1/webhooks/",
    "/api/v1/merchants/pairing",
)
# The customer endpoints use the customer session token instead (test_customer_openapi_document).
CUSTOMER_PATH_PREFIX = "/api/v1/customer-sessions"


@pytest.fixture(scope="module")
def openapi_document() -> dict[str, Any]:
    """Builds the document once for the module."""
    return build_openapi_document()


def iterate_property_schemas(node: object) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yields every (property name, schema) pair found anywhere in the document."""
    if isinstance(node, dict):
        yield from node.get("properties", {}).items()
        for child in node.values():
            yield from iterate_property_schemas(child)
    elif isinstance(node, list):
        for child in node:
            yield from iterate_property_schemas(child)


def list_parameter_and_property_names(document: dict[str, Any]) -> list[str]:
    """Lists every property name and every parameter name of every operation."""
    names = [name for name, _ in iterate_property_schemas(document)]
    for path_item in document["paths"].values():
        for operation in path_item.values():
            names.extend(parameter["name"] for parameter in operation.get("parameters", []))
    return names


def list_non_null_types(property_schema: dict[str, Any]) -> list[object]:
    """Gives the types a property may take, ignoring the null branch of an optional value."""
    branches = property_schema.get("anyOf", [property_schema])
    return [branch.get("type") for branch in branches if branch.get("type") != "null"]


def list_operations(document: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Lists every operation with a readable id such as "GET /api/v1/offers"."""
    return [
        (f"{method.upper()} {path}", operation)
        for path, path_item in document["paths"].items()
        for method, operation in path_item.items()
        if method in HTTP_METHODS
    ]


def test_committed_openapi_document_matches_a_fresh_export() -> None:
    """`make openapi` was run after the last API change (CI sync check)."""
    assert COMMITTED_OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi_document()


def test_openapi_document_is_valid(openapi_document: dict[str, Any]) -> None:
    """The document validates against the OpenAPI specification."""
    validate(openapi_document)


def test_every_in_paise_property_and_parameter_is_an_integer(
    openapi_document: dict[str, Any],
) -> None:
    """Money is always integer paise on the wire, never a number or a string."""
    in_paise_types = [
        (name, list_non_null_types(schema))
        for name, schema in iterate_property_schemas(openapi_document)
        if name.endswith("InPaise")
    ]
    for _, operation in list_operations(openapi_document):
        in_paise_types.extend(
            (parameter["name"], list_non_null_types(parameter["schema"]))
            for parameter in operation.get("parameters", [])
            if parameter["name"].endswith("InPaise")
        )
    assert len(in_paise_types) >= 10
    assert all(types == ["integer"] for _, types in in_paise_types), in_paise_types


def test_no_property_is_number_typed(openapi_document: dict[str, Any]) -> None:
    """No field is a JSON number, so no money (or anything else) can travel as a float."""
    number_typed = [
        name
        for name, schema in iterate_property_schemas(openapi_document)
        if "number" in list_non_null_types(schema)
    ]
    assert number_typed == []


def test_no_property_or_parameter_has_a_card_like_name(openapi_document: dict[str, Any]) -> None:
    """No card number, CVV, expiry, PAN or BIN field exists anywhere in the contract."""
    offending_names = [
        name
        for name in list_parameter_and_property_names(openapi_document)
        if CARD_LIKE_WORDS & set(CAMEL_CASE_HUMP.sub(" ", name).replace("_", " ").lower().split())
    ]
    assert offending_names == []


def test_every_operation_has_summary_description_and_a_problem_response(
    openapi_document: dict[str, Any],
) -> None:
    """Each endpoint documents itself and at least one application/problem+json error."""
    for operation_id, operation in list_operations(openapi_document):
        assert operation.get("summary"), operation_id
        assert operation.get("description"), operation_id
        problem_responses = [
            response
            for status, response in operation["responses"].items()
            if int(status) >= 400 and "application/problem+json" in response.get("content", {})
        ]
        assert problem_responses, operation_id
        assert all(
            "application/json" not in response["content"] for response in problem_responses
        ), operation_id


def test_gateway_operations_say_they_are_unauthenticated(
    openapi_document: dict[str, Any],
) -> None:
    """Offers, the webhook and pairing state that they need no merchant token (ADR 0009)."""
    for operation_id, operation in list_operations(openapi_document):
        if operation_id.split(" ")[1].startswith(UNAUTHENTICATED_PATH_PREFIXES):
            assert "unauthenticated" in operation["description"].lower() or (
                "no credentials" in operation["description"]
            ), operation_id
            assert "security" not in operation, operation_id


def test_merchant_operations_require_the_merchant_bearer_token(
    openapi_document: dict[str, Any],
) -> None:
    """Every other non-customer /api/v1 operation declares the bearer scheme and its 401."""
    merchant_operations = [
        (operation_id, operation)
        for operation_id, operation in list_operations(openapi_document)
        if operation_id.split(" ")[1].startswith("/api/v1/")
        and not operation_id.split(" ")[1].startswith(
            (*UNAUTHENTICATED_PATH_PREFIXES, CUSTOMER_PATH_PREFIX)
        )
    ]
    assert {operation_id for operation_id, _ in merchant_operations} >= {
        "GET /api/v1/merchants/me",
        "GET /api/v1/products",
        "POST /api/v1/payment-links",
        "GET /api/v1/payments/{orderId}/status",
    }
    for operation_id, operation in merchant_operations:
        assert operation["security"] == [{"MerchantBearerToken": []}], operation_id
        assert "MERCHANT_AUTHENTICATION_REQUIRED" in json.dumps(operation["responses"]["401"]), (
            operation_id
        )
    assert openapi_document["components"]["securitySchemes"]["MerchantBearerToken"] == {
        "type": "http",
        "scheme": "bearer",
        "description": openapi_document["components"]["securitySchemes"]["MerchantBearerToken"][
            "description"
        ],
    }


def test_every_too_many_requests_answer_documents_retry_after(
    openapi_document: dict[str, Any],
) -> None:
    """A 429 always tells the client when to try again."""
    too_many_requests_answers = [
        (operation_id, operation["responses"]["429"])
        for operation_id, operation in list_operations(openapi_document)
        if "429" in operation["responses"]
    ]
    assert {operation_id for operation_id, _ in too_many_requests_answers} == {
        "POST /api/v1/merchants/pairing",
        "POST /api/v1/sales/{saleId}/payment-links",
        "GET /api/v1/sales/{saleId}/payment-status",
        "POST /api/v1/payment-links",
        "GET /api/v1/payments/{orderId}/status",
        "POST /api/v1/webhooks/paytm",
        "POST /api/v1/customer-sessions",
        "POST /api/v1/customer-sessions/{customerSessionId}/consent/otp",
        "POST /api/v1/customer-sessions/{customerSessionId}/consent",
        "POST /api/v1/customer-sessions/{customerSessionId}/speech/transcriptions",
        "POST /api/v1/customer-sessions/{customerSessionId}/speech/synthesis",
        "POST /api/v1/customer-sessions/{customerSessionId}/teach-back",
    }
    for _, response in too_many_requests_answers:
        assert response["headers"]["Retry-After"]["schema"] == {"type": "integer", "minimum": 1}


def test_pairing_pin_is_write_only_text_of_six_digits(openapi_document: dict[str, Any]) -> None:
    """The PIN is text (leading zeros survive), never echoed back, and never shown in docs."""
    pin_schema = openapi_document["components"]["schemas"]["PairDeviceRequest"]["properties"]["pin"]
    assert pin_schema["type"] == "string"
    assert pin_schema["pattern"] == "^[0-9]{6}$"
    assert pin_schema["writeOnly"] is True
    assert pin_schema["format"] == "password"


def test_committed_openapi_document_is_json() -> None:
    """The committed file parses as JSON, so the frontend generator can read it."""
    assert json.loads(COMMITTED_OPENAPI_PATH.read_text(encoding="utf-8"))["openapi"] == "3.1.0"


def test_openapi_document_is_built_once_and_cached() -> None:
    """The schema is generated on first request and then served from the cache."""
    application = create_application(ApplicationSettings())
    assert application.openapi() is application.openapi()


def test_sale_event_stream_documents_its_payload_under_text_event_stream_only(
    openapi_document: dict[str, Any],
) -> None:
    """The stream's 200 is text/event-stream with the pinned payload schema, never JSON."""
    success_content = openapi_document["paths"]["/api/v1/sales/events"]["get"]["responses"]["200"][
        "content"
    ]
    assert set(success_content) == {"text/event-stream"}
    assert success_content["text/event-stream"]["schema"] == {
        "$ref": "#/components/schemas/SaleStatusEventPayload"
    }


def test_only_the_sale_less_payment_link_operation_is_deprecated_and_it_sends_no_location(
    openapi_document: dict[str, Any],
) -> None:
    """The bare Layer 1 link points callers to the sale's own links and promises no Location."""
    deprecated_operations = [
        (path, method)
        for path, path_item in openapi_document["paths"].items()
        for method, operation in path_item.items()
        if operation.get("deprecated")
    ]
    assert deprecated_operations == [("/api/v1/payment-links", "post")]
    operation = openapi_document["paths"]["/api/v1/payment-links"]["post"]
    assert "/api/v1/sales/{saleId}/payment-links" in operation["description"]
    assert "headers" not in operation["responses"]["201"]
