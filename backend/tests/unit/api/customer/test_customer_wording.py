"""Customer code and the customer contract never use credit-decision or pressure wording."""

import json
from pathlib import Path
from typing import Any

import pytest

from emi_copilot.api.openapi_export import build_openapi_document
from tests.contract.test_merchant_response_privacy import iterate_schema_references
from tests.unit.architecture.source_files import APPLICATION_SOURCE_ROOT, describe_source_file

BANNED_PHRASES = ("approved", "declined", "eligible", "rejected", "best for you", "interest rate")
CUSTOMER_MODULE_PATTERNS = (
    "services/customer/*.py",
    "services/plan_advice_*.py",
    "dtos/customer_*.py",
    "dtos/comfort_check_dtos.py",
    "dtos/plan_alternative_dtos.py",
    "api/controllers/customer_*.py",
    "api/controllers/comfort_check_controller.py",
    "api/customer_*.py",
    "domain/comfort/*.py",
    "domain/ranking/*.py",
    "domain/alternatives/*.py",
    "adapters/financial_profile/*.py",
)


def list_customer_modules() -> list[Path]:
    """Lists every customer-flow module, sorted so test ids are stable."""
    return sorted(
        {
            path
            for pattern in CUSTOMER_MODULE_PATTERNS
            for path in APPLICATION_SOURCE_ROOT.glob(pattern)
        }
    )


IDENTIFIERS_NOT_SHOWN_TO_CUSTOMERS = ("QrTokenRejectedError",)
"""Class names from core/ that customer modules import; code names, never customer wording."""


def find_banned_phrases(text: str) -> list[str]:
    """Lists the banned phrases found in the text, ignoring case and the listed code names."""
    for identifier in IDENTIFIERS_NOT_SHOWN_TO_CUSTOMERS:
        text = text.replace(identifier, "")
    lowered_text = text.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lowered_text]


def test_customer_modules_are_found() -> None:
    """Guards the wording test against silently checking nothing."""
    assert len(list_customer_modules()) >= 30


@pytest.mark.parametrize("customer_module", list_customer_modules(), ids=describe_source_file)
def test_customer_module_has_no_banned_wording(customer_module: Path) -> None:
    """No credit-decision words, no "best for you", no interest rates (CLAUDE.md section 2)."""
    assert find_banned_phrases(customer_module.read_text(encoding="utf-8")) == []


def collect_customer_contract(document: dict[str, Any]) -> dict[str, Any]:
    """Gives the customer path items and every component schema they reach through $refs."""
    path_items = {
        path: path_item
        for path, path_item in document["paths"].items()
        if path.startswith("/api/v1/customer-sessions")
    }
    schemas: dict[str, Any] = {}
    pending_names = list(iterate_schema_references(path_items))
    while pending_names:
        schema_name = pending_names.pop()
        if schema_name not in schemas:
            schemas[schema_name] = document["components"]["schemas"][schema_name]
            pending_names.extend(iterate_schema_references(schemas[schema_name]))
    return {"paths": path_items, "schemas": schemas}


def test_customer_openapi_contract_has_no_banned_wording() -> None:
    """The customer operations and every schema they use avoid the same wording."""
    customer_contract = collect_customer_contract(build_openapi_document())
    assert len(customer_contract["paths"]) == 10
    document_text = json.dumps(customer_contract, ensure_ascii=False)
    assert find_banned_phrases(document_text) == []


def test_find_banned_phrases_ignores_case() -> None:
    """The rule itself finds a phrase however it is capitalised."""
    assert find_banned_phrases("Best For You and APPROVED") == ["approved", "best for you"]


def test_find_banned_phrases_ignores_only_the_listed_code_names() -> None:
    """A listed core class name is not wording; the same word anywhere else still is."""
    assert find_banned_phrases("except QrTokenRejectedError") == []
    assert find_banned_phrases("the QR was rejected") == ["rejected"]
