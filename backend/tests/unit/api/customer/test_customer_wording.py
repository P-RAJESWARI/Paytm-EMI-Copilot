"""Customer code and the customer contract never use credit-decision or pressure wording."""

import json
from pathlib import Path

import pytest

from emi_copilot.api.customer_contract_application import build_customer_contract_application
from tests.unit.architecture.source_files import APPLICATION_SOURCE_ROOT, describe_source_file

BANNED_PHRASES = ("approved", "declined", "eligible", "rejected", "best for you", "interest rate")
CUSTOMER_MODULE_PATTERNS = (
    "services/customer_flow/*.py",
    "services/plan_advice_*.py",
    "dtos/customer_*.py",
    "dtos/comfort_check_dtos.py",
    "dtos/plan_alternative_dtos.py",
    "api/controllers/customer_*.py",
    "api/controllers/comfort_check_controller.py",
    "api/customer_contract_application.py",
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


def find_banned_phrases(text: str) -> list[str]:
    """Lists the banned phrases found in the text, ignoring case."""
    lowered_text = text.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lowered_text]


def test_customer_modules_are_found() -> None:
    """Guards the wording test against silently checking nothing."""
    assert len(list_customer_modules()) >= 30


@pytest.mark.parametrize("customer_module", list_customer_modules(), ids=describe_source_file)
def test_customer_module_has_no_banned_wording(customer_module: Path) -> None:
    """No credit-decision words, no "best for you", no interest rates (CLAUDE.md section 2)."""
    assert find_banned_phrases(customer_module.read_text(encoding="utf-8")) == []


def test_customer_openapi_document_has_no_banned_wording() -> None:
    """The published customer contract avoids the same wording."""
    document_text = json.dumps(build_customer_contract_application().openapi(), ensure_ascii=False)
    assert find_banned_phrases(document_text) == []


def test_find_banned_phrases_ignores_case() -> None:
    """The rule itself finds a phrase however it is capitalised."""
    assert find_banned_phrases("Best For You and APPROVED") == ["approved", "best for you"]
