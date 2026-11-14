"""The committed customer contract is current, valid and keeps the money, card and STUB rules."""

from pathlib import Path
from typing import Any

import pytest
from openapi_spec_validator import validate

from emi_copilot.api.customer_contract_openapi_export import (
    build_customer_openapi_document,
    render_customer_openapi_document,
)
from tests.unit.api.test_openapi_document import (
    CAMEL_CASE_HUMP,
    CARD_LIKE_WORDS,
    iterate_property_schemas,
    list_non_null_types,
    list_operations,
    list_parameter_and_property_names,
)

COMMITTED_CUSTOMER_OPENAPI_PATH = Path(__file__).resolve().parents[3] / "openapi.customer.json"
STUB_DESCRIPTION_START = (
    "STUB (DESIGN_SPEC §4 sample data) until Phase 3C; not mounted in the main app (ADR 0012)."
)
SESSION_CREATION_OPERATION = "POST /api/v1/customer-sessions"
CONSENT_OPERATION = "POST /api/v1/customer-sessions/{customerSessionId}/consent"
SESSION_TOKEN_SCHEME: dict[str, list[str]] = {"CustomerSessionToken": []}
INTEGER_SUFFIXES = ("InPaise", "InBasisPoints")


@pytest.fixture(scope="module")
def customer_openapi_document() -> dict[str, Any]:
    """Builds the customer document once for the module."""
    return build_customer_openapi_document()


def test_committed_customer_openapi_document_matches_a_fresh_export() -> None:
    """`make openapi-customer` was run after the last customer API change."""
    committed_text = COMMITTED_CUSTOMER_OPENAPI_PATH.read_text(encoding="utf-8")
    assert committed_text == render_customer_openapi_document()


def test_customer_openapi_document_is_valid(customer_openapi_document: dict[str, Any]) -> None:
    """The document validates against the OpenAPI specification."""
    validate(customer_openapi_document)


def test_every_money_and_basis_point_property_is_an_integer(
    customer_openapi_document: dict[str, Any],
) -> None:
    """Paise and basis points are integers on the wire, never numbers or strings."""
    integer_property_types = [
        (name, list_non_null_types(schema))
        for name, schema in iterate_property_schemas(customer_openapi_document)
        if name.endswith(INTEGER_SUFFIXES)
    ]
    assert len(integer_property_types) >= 20
    assert any(name.endswith("InBasisPoints") for name, _ in integer_property_types)
    assert all(types == ["integer"] for _, types in integer_property_types), integer_property_types


def test_no_customer_property_is_number_typed(customer_openapi_document: dict[str, Any]) -> None:
    """No field is a JSON number, so no money or ratio travels as a float."""
    number_typed = [
        name
        for name, schema in iterate_property_schemas(customer_openapi_document)
        if "number" in list_non_null_types(schema)
    ]
    assert number_typed == []


def test_no_customer_property_or_parameter_has_a_card_like_name(
    customer_openapi_document: dict[str, Any],
) -> None:
    """No card number, CVV, expiry, PAN or BIN field exists in the customer contract."""
    offending_names = [
        name
        for name in list_parameter_and_property_names(customer_openapi_document)
        if CARD_LIKE_WORDS & set(CAMEL_CASE_HUMP.sub(" ", name).replace("_", " ").lower().split())
    ]
    assert offending_names == []


def test_every_customer_operation_is_labelled_stub_and_documents_problems(
    customer_openapi_document: dict[str, Any],
) -> None:
    """Each operation starts with the STUB note and documents application/problem+json errors."""
    operations = list_operations(customer_openapi_document)
    assert len(operations) == 8
    for operation_id, operation in operations:
        assert operation["summary"], operation_id
        assert operation["description"].startswith(STUB_DESCRIPTION_START), operation_id
        assert any(
            int(status) >= 400 and "application/problem+json" in response.get("content", {})
            for status, response in operation["responses"].items()
        ), operation_id


def test_consent_requires_an_idempotency_key(customer_openapi_document: dict[str, Any]) -> None:
    """Consent records evidence, so the Idempotency-Key header is required."""
    (consent_operation,) = [
        operation
        for operation_id, operation in list_operations(customer_openapi_document)
        if operation_id == CONSENT_OPERATION
    ]
    (idempotency_key_parameter,) = [
        parameter
        for parameter in consent_operation["parameters"]
        if parameter["name"] == "Idempotency-Key"
    ]
    assert idempotency_key_parameter["in"] == "header"
    assert idempotency_key_parameter["required"] is True


def test_session_token_header_guards_every_operation_but_session_creation(
    customer_openapi_document: dict[str, Any],
) -> None:
    """X-Customer-Session-Token is an API-key header on every call after the QR is scanned."""
    security_scheme = customer_openapi_document["components"]["securitySchemes"]
    assert security_scheme["CustomerSessionToken"]["type"] == "apiKey"
    assert security_scheme["CustomerSessionToken"]["in"] == "header"
    assert security_scheme["CustomerSessionToken"]["name"] == "X-Customer-Session-Token"
    for operation_id, operation in list_operations(customer_openapi_document):
        expected_security = (
            [] if operation_id == SESSION_CREATION_OPERATION else [SESSION_TOKEN_SCHEME]
        )
        assert operation.get("security", []) == expected_security, operation_id
