"""Merchant responses expose exactly the allowed fields and no customer detail (rule 6).

The committed openapi.json (the contract the frontend client is generated from) is read, every
schema reachable from a merchant endpoint's responses is collected through $refs, and its
property names must equal the allow-list exactly. No property anywhere in them may name income,
existing EMIs, comfort, ratios, basis points, steps, progress, scanning or a budget.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.contract.merchant_response_allow_list import (
    ALLOWED_PROPERTIES_BY_SCHEMA,
    LAYER_1_GATEWAY_PATH_PREFIXES,
    MERCHANT_PATH_PREFIXES,
    MERCHANT_SALE_STATUSES,
    SCHEMAS_ALLOWED_A_BUDGET_PROPERTY,
)

COMMITTED_OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.json"
SCHEMA_REFERENCE_PREFIX = "#/components/schemas/"
HTTP_METHODS = frozenset({"get", "put", "post", "delete", "patch"})
CAMEL_CASE_HUMP = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
BANNED_WORD_SEQUENCES = (
    ("income",),
    ("existing", "emi"),
    ("comfort",),
    ("ratio",),
    ("basis", "points"),
    ("step",),
    ("progress",),
    ("scanned",),
    ("budget",),
)
"""Customer detail a merchant must never see; each word also matches its plural or longer form."""
BUDGET_WORDS = ("budget",)


def split_into_lowercase_words(property_name: str) -> list[str]:
    """Splits camelCase and snake_case into lowercase words: "existingEmiInPaise" -> 4 words."""
    return CAMEL_CASE_HUMP.sub(" ", property_name).replace("_", " ").lower().split()


def find_banned_word_sequence(property_name: str) -> tuple[str, ...] | None:
    """Gives the banned words a property name contains, or None when it is clean.

    Words match at word starts ("steps" matches "step", "duration" does not match "ratio"), and
    a multi-word pattern also matches when run together ("existingemi").
    """
    words = split_into_lowercase_words(property_name)
    joined_name = "".join(words)
    for banned_sequence in BANNED_WORD_SEQUENCES:
        length = len(banned_sequence)
        for start in range(len(words) - length + 1):
            window = words[start : start + length]
            if all(
                word.startswith(banned)
                for word, banned in zip(window, banned_sequence, strict=True)
            ):
                return banned_sequence
        if length > 1 and "".join(banned_sequence) in joined_name:
            return banned_sequence
    return None


def list_privacy_violations(
    properties_by_schema: dict[str, set[str]],
    schemas_allowed_a_budget: frozenset[str] = SCHEMAS_ALLOWED_A_BUDGET_PROPERTY,
) -> list[str]:
    """Lists every "Schema.property (banned: words)" found; a budget only where allowed."""
    violations = []
    for schema_name, property_names in sorted(properties_by_schema.items()):
        for property_name in sorted(property_names):
            banned_sequence = find_banned_word_sequence(property_name)
            if banned_sequence is None or (
                banned_sequence == BUDGET_WORDS and schema_name in schemas_allowed_a_budget
            ):
                continue
            violations.append(
                f"{schema_name}.{property_name} (banned: {' '.join(banned_sequence)})"
            )
    return violations


def iterate_schema_references(node: object) -> Iterator[str]:
    """Yields the name of every component schema a node refers to, at any depth."""
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str) and reference.startswith(SCHEMA_REFERENCE_PREFIX):
            yield reference.removeprefix(SCHEMA_REFERENCE_PREFIX)
        for child in node.values():
            yield from iterate_schema_references(child)
    elif isinstance(node, list):
        for child in node:
            yield from iterate_schema_references(child)


def list_merchant_operations(document: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Lists every operation under a merchant path prefix as ("GET /path", operation)."""
    return [
        (f"{method.upper()} {path}", operation)
        for path, path_item in document["paths"].items()
        if path.startswith(MERCHANT_PATH_PREFIXES)
        for method, operation in path_item.items()
        if method in HTTP_METHODS
    ]


def collect_reachable_properties(document: dict[str, Any]) -> dict[str, set[str]]:
    """Follows $refs from every merchant response (success and error) to every schema they reach.

    Gives each reached schema's property names; an inline response schema is checked too, under
    the name of its operation and status.
    """
    component_schemas = document["components"]["schemas"]
    properties_by_schema: dict[str, set[str]] = {}
    pending_names: list[str] = []
    for operation_id, operation in list_merchant_operations(document):
        for status, response in operation["responses"].items():
            for media_type, content in response.get("content", {}).items():
                schema = content.get("schema", {})
                if "properties" in schema:
                    inline_name = f"{operation_id} {status} {media_type}"
                    properties_by_schema[inline_name] = set(schema["properties"])
                pending_names.extend(iterate_schema_references(schema))
    while pending_names:
        schema_name = pending_names.pop()
        if schema_name in properties_by_schema:
            continue
        schema = component_schemas[schema_name]
        properties_by_schema[schema_name] = set(schema.get("properties", {}))
        pending_names.extend(iterate_schema_references(schema))
    return properties_by_schema


@pytest.fixture(scope="module")
def committed_document() -> dict[str, Any]:
    """Reads the committed openapi.json, the contract the merchant app is generated from."""
    document: dict[str, Any] = json.loads(COMMITTED_OPENAPI_PATH.read_text(encoding="utf-8"))
    return document


def test_every_api_path_is_classified_as_merchant_or_layer_1_gateway(
    committed_document: dict[str, Any],
) -> None:
    """A new endpoint cannot slip past this test by sitting under an unlisted prefix."""
    unclassified_paths = [
        path
        for path in committed_document["paths"]
        if path.startswith("/api/v1/")
        and not path.startswith(MERCHANT_PATH_PREFIXES + LAYER_1_GATEWAY_PATH_PREFIXES)
    ]
    assert unclassified_paths == [], f"Classify these paths in the allow-list: {unclassified_paths}"


def test_merchant_operations_include_pairing_profile_products_sales_and_reports(
    committed_document: dict[str, Any],
) -> None:
    """The check really covers every merchant endpoint of steps 2.1 to 2.4."""
    assert {operation_id for operation_id, _ in list_merchant_operations(committed_document)} == {
        "POST /api/v1/merchants/pairing",
        "GET /api/v1/merchants/me",
        "GET /api/v1/products",
        "POST /api/v1/sales",
        "GET /api/v1/sales",
        "GET /api/v1/sales/events",
        "GET /api/v1/sales/{saleId}",
        "POST /api/v1/sales/{saleId}/qr-tokens",
        "GET /api/v1/sales/{saleId}/handoff",
        "POST /api/v1/sales/{saleId}/payment-links",
        "GET /api/v1/sales/{saleId}/payment-status",
        "POST /api/v1/payment-links",
        "GET /api/v1/payments/{orderId}/status",
        "GET /api/v1/reports/funnel",
        "GET /api/v1/reports/missed-sales",
        "GET /api/v1/reports/suggested-actions",
        "GET /api/v1/reports/money-due",
        "GET /api/v1/reports/weekly-message",
        "POST /api/v1/reports/weekly-message/send",
    }


def test_merchant_response_schemas_have_exactly_the_allowed_properties(
    committed_document: dict[str, Any],
) -> None:
    """Each reachable schema, and no other, is listed with exactly its property names."""
    reachable_properties = collect_reachable_properties(committed_document)
    unexpected_schemas = sorted(set(reachable_properties) - set(ALLOWED_PROPERTIES_BY_SCHEMA))
    missing_schemas = sorted(set(ALLOWED_PROPERTIES_BY_SCHEMA) - set(reachable_properties))
    assert unexpected_schemas == [], f"Schemas not on the allow-list: {unexpected_schemas}"
    assert missing_schemas == [], (
        f"Allow-listed schemas no merchant response uses: {missing_schemas}"
    )
    field_differences = {
        schema_name: {
            "not allowed": sorted(property_names - ALLOWED_PROPERTIES_BY_SCHEMA[schema_name]),
            "missing": sorted(ALLOWED_PROPERTIES_BY_SCHEMA[schema_name] - property_names),
        }
        for schema_name, property_names in reachable_properties.items()
        if property_names != ALLOWED_PROPERTIES_BY_SCHEMA[schema_name]
    }
    assert field_differences == {}, f"Merchant response fields differ: {field_differences}"


def test_no_merchant_response_property_names_customer_detail(
    committed_document: dict[str, Any],
) -> None:
    """No income, EMIs, comfort, ratio, basis points, step, progress, scan or budget field."""
    violations = list_privacy_violations(collect_reachable_properties(committed_document))
    assert violations == [], "Merchant responses expose customer detail: " + ", ".join(violations)


def test_sale_status_enum_is_exactly_the_five_merchant_statuses(
    committed_document: dict[str, Any],
) -> None:
    """Plan Q2: no "not scanned yet" or any other customer step can appear as a status."""
    sale_status_schema = committed_document["components"]["schemas"]["SaleStatus"]
    assert tuple(sale_status_schema["enum"]) == MERCHANT_SALE_STATUSES


@pytest.mark.parametrize(
    ("property_name", "expected_banned_words"),
    [
        ("monthlyIncomeInPaise", ("income",)),
        ("existingEmiInPaise", ("existing", "emi")),
        ("existingemis", ("existing", "emi")),
        ("comfortBand", ("comfort",)),
        ("comfortRatioInBasisPoints", ("comfort",)),
        ("debtRatio", ("ratio",)),
        ("shareInBasisPoints", ("basis", "points")),
        ("currentStep", ("step",)),
        ("completedSteps", ("step",)),
        ("progressPercent", ("progress",)),
        ("isQrScanned", ("scanned",)),
        ("monthlyBudgetInPaise", ("budget",)),
        ("BUDGET", ("budget",)),
    ],
)
def test_banned_word_matcher_catches_customer_detail_in_any_casing(
    property_name: str, expected_banned_words: tuple[str, ...]
) -> None:
    """The matcher itself finds every banned pattern, ignoring case and word joins."""
    assert find_banned_word_sequence(property_name) == expected_banned_words


@pytest.mark.parametrize(
    "property_name",
    ["durationInSeconds", "statusChangedAt", "totalPayableInPaise", "sessionCode", "emiType"],
)
def test_banned_word_matcher_leaves_ordinary_merchant_fields_alone(property_name: str) -> None:
    """Words are matched at word starts, so "duration" is not a ratio."""
    assert find_banned_word_sequence(property_name) is None


def test_privacy_violations_name_the_offending_schema_and_field() -> None:
    """A failure message says exactly which field to remove."""
    violations = list_privacy_violations(
        {"SaleSummaryResponse": {"saleId", "comfortBand"}, "BudgetBucketResponse": {"budgetFrom"}}
    )
    assert violations == [
        "BudgetBucketResponse.budgetFrom (banned: budget)",
        "SaleSummaryResponse.comfortBand (banned: comfort)",
    ]


def test_budget_is_allowed_only_in_a_schema_listed_for_it() -> None:
    """Step 2.4's aggregate bucket schema can name a budget; nothing else can."""
    properties = {"BudgetBucketResponse": {"budgetFrom"}, "SaleSummaryResponse": {"budget"}}
    assert list_privacy_violations(properties, frozenset({"BudgetBucketResponse"})) == [
        "SaleSummaryResponse.budget (banned: budget)"
    ]
