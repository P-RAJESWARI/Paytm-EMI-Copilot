"""The customer operations in openapi.json: mounted, documented, token-guarded and calm."""

import json
from typing import Any

import pytest

from emi_copilot.api.openapi_export import build_openapi_document
from tests.unit.api.test_openapi_document import (
    iterate_property_schemas,
    list_non_null_types,
    list_operations,
)

CUSTOMER_PATH_PREFIX = "/api/v1/customer-sessions"
SESSION_PATH = CUSTOMER_PATH_PREFIX + "/{customerSessionId}"
SESSION_CREATION_OPERATION = "POST /api/v1/customer-sessions"
CONSENT_OPERATION = f"POST {SESSION_PATH}/consent"
EXPLANATION_OPERATION = f"POST {SESSION_PATH}/explanation"
SESSION_TOKEN_SCHEME: dict[str, list[str]] = {"CustomerSessionToken": []}
CUSTOMER_PROBLEM_SCHEMA = {"$ref": "#/components/schemas/CustomerProblemDetailsResponse"}
CUSTOMER_DESCRIPTION_START = "Customer endpoint, opened from the shop's QR"


@pytest.fixture(scope="module")
def openapi_document() -> dict[str, Any]:
    """Builds the main document once for the module."""
    return build_openapi_document()


def list_customer_operations(document: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Lists the operations under /api/v1/customer-sessions as ("POST /path", operation)."""
    return [
        (operation_id, operation)
        for operation_id, operation in list_operations(document)
        if operation_id.split(" ")[1].startswith(CUSTOMER_PATH_PREFIX)
    ]


def find_operation(document: dict[str, Any], wanted_operation_id: str) -> dict[str, Any]:
    """Gives one operation by its "METHOD /path" id."""
    (operation,) = [
        operation
        for operation_id, operation in list_operations(document)
        if operation_id == wanted_operation_id
    ]
    return operation


def test_main_document_mounts_exactly_the_thirteen_customer_operations(
    openapi_document: dict[str, Any],
) -> None:
    """The customer routers live in the main app (ADR 0022 decision 6), voice included."""
    assert {operation_id for operation_id, _ in list_customer_operations(openapi_document)} == {
        SESSION_CREATION_OPERATION,
        f"GET {SESSION_PATH}",
        f"PUT {SESSION_PATH}/budget",
        f"POST {SESSION_PATH}/comfort-check",
        f"GET {SESSION_PATH}/plans",
        f"POST {SESSION_PATH}/alternatives",
        EXPLANATION_OPERATION,
        f"POST {SESSION_PATH}/speech/transcriptions",
        f"POST {SESSION_PATH}/speech/synthesis",
        f"POST {SESSION_PATH}/teach-back",
        f"POST {SESSION_PATH}/consent/otp",
        CONSENT_OPERATION,
        f"GET {SESSION_PATH}/receipt",
    }


def test_every_customer_operation_is_described_and_answers_customer_problems(
    openapi_document: dict[str, Any],
) -> None:
    """Each starts with the customer note, and every problem uses the customer problem schema."""
    for operation_id, operation in list_customer_operations(openapi_document):
        assert operation["summary"], operation_id
        assert operation["description"].startswith(CUSTOMER_DESCRIPTION_START), operation_id
        problem_contents = [
            response["content"]["application/problem+json"]
            for status, response in operation["responses"].items()
            if int(status) >= 400
        ]
        assert problem_contents, operation_id
        assert all(content["schema"] == CUSTOMER_PROBLEM_SCHEMA for content in problem_contents), (
            operation_id
        )


def test_session_token_header_guards_every_operation_but_the_qr_exchange(
    openapi_document: dict[str, Any],
) -> None:
    """X-Customer-Session-Token is an API-key header on every call after the QR exchange."""
    security_scheme = openapi_document["components"]["securitySchemes"]["CustomerSessionToken"]
    assert security_scheme["type"] == "apiKey"
    assert security_scheme["in"] == "header"
    assert security_scheme["name"] == "X-Customer-Session-Token"
    for operation_id, operation in list_customer_operations(openapi_document):
        expected_security = (
            [] if operation_id == SESSION_CREATION_OPERATION else [SESSION_TOKEN_SCHEME]
        )
        assert operation.get("security", []) == expected_security, operation_id
    assert (
        "No credentials"
        in find_operation(openapi_document, SESSION_CREATION_OPERATION)["description"]
    )


def test_consent_requires_an_idempotency_key_and_reads_the_language(
    openapi_document: dict[str, Any],
) -> None:
    """Consent records evidence, so Idempotency-Key is required; Accept-Language is optional."""
    parameters = {
        parameter["name"]: parameter
        for parameter in find_operation(openapi_document, CONSENT_OPERATION)["parameters"]
    }
    assert parameters["Idempotency-Key"]["in"] == "header"
    assert parameters["Idempotency-Key"]["required"] is True
    assert parameters["Accept-Language"]["in"] == "header"
    assert parameters["Accept-Language"]["required"] is False


def test_consent_request_names_only_the_offer_the_shown_figures_and_the_code(
    openapi_document: dict[str, Any],
) -> None:
    """ADR 0022 decision 1 removed productId and downPaymentInPaise from consent."""
    request_schema = openapi_document["components"]["schemas"]["GiveConsentRequest"]
    assert set(request_schema["properties"]) == {
        "offerId",
        "shownMonthlyInstallmentInPaise",
        "shownTotalPayableInPaise",
        "otp",
        "hasAgreedToPlan",
    }


def test_explanation_reads_accept_language(openapi_document: dict[str, Any]) -> None:
    """The explanation's language comes from an optional Accept-Language header."""
    (accept_language,) = [
        parameter
        for parameter in find_operation(openapi_document, EXPLANATION_OPERATION)["parameters"]
        if parameter["name"] == "Accept-Language"
    ]
    assert accept_language["in"] == "header"
    assert accept_language["required"] is False


def test_wrong_code_problem_documents_attempts_remaining(openapi_document: dict[str, Any]) -> None:
    """OTP_INCORRECT carries attemptsRemaining in its example and in the problem schema."""
    consent_operation = find_operation(openapi_document, CONSENT_OPERATION)
    examples = consent_operation["responses"]["422"]["content"]["application/problem+json"][
        "examples"
    ]
    assert examples["OTP_INCORRECT"]["value"]["attemptsRemaining"] == 2
    assert "attemptsRemaining" not in examples["OTP_EXPIRED"]["value"]
    problem_schema = openapi_document["components"]["schemas"]["CustomerProblemDetailsResponse"]
    assert list_non_null_types(problem_schema["properties"]["attemptsRemaining"]) == ["integer"]
    assert "attemptsRemaining" not in problem_schema.get("required", [])


def test_every_basis_point_property_is_an_integer(openapi_document: dict[str, Any]) -> None:
    """Shares travel as integer basis points, never as a float percentage."""
    basis_point_types = [
        (name, list_non_null_types(schema))
        for name, schema in iterate_property_schemas(openapi_document)
        if name.endswith("InBasisPoints")
    ]
    assert len(basis_point_types) >= 3
    assert all(types == ["integer"] for _, types in basis_point_types), basis_point_types


def test_no_stub_wording_is_left_in_the_document(openapi_document: dict[str, Any]) -> None:
    """The Phase 3A stub notes and sample tokens are gone with the stubs."""
    document_text = json.dumps(openapi_document).lower()
    assert "stub" not in document_text
