"""Import boundaries: domain/ and the gateway port import only the standard library and domain/."""

import ast
import sys
from pathlib import Path

import pytest

from tests.unit.architecture.source_files import (
    PAYMENT_GATEWAY_PORT_FILE,
    describe_source_file,
    list_domain_modules,
)

ALLOWED_APPLICATION_PACKAGE = "emi_copilot.domain"


def list_imported_module_names(source_file: Path) -> list[str]:
    """Lists every module a file imports; relative imports are kept with their leading dots."""
    syntax_tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
    imported_module_names: list[str] = []
    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            imported_module_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_module_names.append("." * node.level + (node.module or ""))
    return imported_module_names


def is_allowed_import(module_name: str) -> bool:
    """Tells whether a module is in the standard library or inside emi_copilot.domain."""
    top_level_package = module_name.split(".", maxsplit=1)[0]
    is_inside_domain = module_name == ALLOWED_APPLICATION_PACKAGE or module_name.startswith(
        ALLOWED_APPLICATION_PACKAGE + "."
    )
    return top_level_package in sys.stdlib_module_names or is_inside_domain


def find_disallowed_imports(source_file: Path) -> list[str]:
    """Lists the imports of a file that are neither standard library nor domain/."""
    return [
        module_name
        for module_name in list_imported_module_names(source_file)
        if not is_allowed_import(module_name)
    ]


def test_domain_has_modules_to_check() -> None:
    """Guards the boundary test against silently checking nothing if the package moves."""
    assert len(list_domain_modules()) > 10


@pytest.mark.parametrize("domain_module", list_domain_modules(), ids=describe_source_file)
def test_domain_module_imports_only_standard_library_and_domain(domain_module: Path) -> None:
    """Domain code stays pure: no framework, database, HTTP or other application layer."""
    assert find_disallowed_imports(domain_module) == []


def test_payment_gateway_port_imports_only_standard_library_and_domain() -> None:
    """The port is expressed in domain terms, so it cannot depend on any vendor or library."""
    assert find_disallowed_imports(PAYMENT_GATEWAY_PORT_FILE) == []


@pytest.mark.parametrize(
    ("module_name", "expected_allowed"),
    [
        ("decimal", True),
        ("collections.abc", True),
        ("emi_copilot.domain", True),
        ("emi_copilot.domain.payments.emi_type", True),
        ("emi_copilot.domain_extras", False),
        ("emi_copilot.repositories.database", False),
        ("sqlalchemy", False),
        ("httpx", False),
        (".money", False),
    ],
)
def test_is_allowed_import_accepts_only_standard_library_and_domain(
    module_name: str, *, expected_allowed: bool
) -> None:
    """The rule itself rejects third-party, other-layer, look-alike and relative imports."""
    assert is_allowed_import(module_name) is expected_allowed


def test_find_disallowed_imports_reports_every_import_form(tmp_path: Path) -> None:
    """Plain, from and nested imports outside the boundary are all reported."""
    sample_module = tmp_path / "sample_module.py"
    sample_module.write_text(
        "import json\n"
        "import httpx\n"
        "from emi_copilot.domain.money import Money\n"
        "from emi_copilot.core.clock import Clock\n"
        "def load() -> None:\n"
        "    from fastapi import FastAPI\n",
        encoding="utf-8",
    )
    assert find_disallowed_imports(sample_module) == ["httpx", "emi_copilot.core.clock", "fastapi"]
