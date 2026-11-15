"""Controllers translate HTTP only; the gateway factory is imported by the composition root only.

Controllers may import services, dtos, domain.errors and the api/ wiring (dependencies,
sale_dependencies and customer_dependencies, the merchant sign-in, customer request context and
rate-limit dependencies, and OpenAPI helpers),
never repositories, adapters, ORM models or other domain modules (backend.md section 2).
Outside adapters/, only api/dependencies.py imports the factory (ADR 0008).
"""

import sys
from pathlib import Path

import pytest

from tests.unit.architecture.source_files import (
    ADAPTERS_DIRECTORY,
    APPLICATION_SOURCE_ROOT,
    describe_source_file,
    list_application_modules,
    list_controller_modules,
)
from tests.unit.architecture.test_import_boundaries import (
    is_inside_package,
    list_imported_module_names,
)

ALLOWED_APPLICATION_MODULES_IN_CONTROLLERS = (
    "emi_copilot.services",
    "emi_copilot.dtos",
    "emi_copilot.domain.errors",
    "emi_copilot.api.dependencies",
    "emi_copilot.api.customer_dependencies",
    "emi_copilot.api.customer_request_context",
    "emi_copilot.api.merchant_authentication",
    "emi_copilot.api.merchant_dependencies",
    "emi_copilot.api.report_dependencies",
    "emi_copilot.api.openapi_documentation",
    "emi_copilot.api.rate_limiting",
    "emi_copilot.api.sale_dependencies",
    "emi_copilot.api.controllers",
)
ALLOWED_FRAMEWORK_PACKAGES_IN_CONTROLLERS = ("fastapi", "starlette")
GATEWAY_FACTORY_MODULE = "emi_copilot.adapters.payment_gateway.factory"
COMPOSITION_ROOT_FILE = APPLICATION_SOURCE_ROOT / "api" / "dependencies.py"


def is_allowed_in_controllers(module_name: str) -> bool:
    """Tells whether a controller may import the module."""
    top_level_package = module_name.split(".", maxsplit=1)[0]
    return (
        top_level_package in sys.stdlib_module_names
        or top_level_package in ALLOWED_FRAMEWORK_PACKAGES_IN_CONTROLLERS
        or any(
            is_inside_package(module_name, allowed_module)
            for allowed_module in ALLOWED_APPLICATION_MODULES_IN_CONTROLLERS
        )
    )


def test_controllers_has_modules_to_check() -> None:
    """Guards the controller boundary test against silently checking nothing."""
    assert len(list_controller_modules()) >= 3


@pytest.mark.parametrize("controller_module", list_controller_modules(), ids=describe_source_file)
def test_controller_imports_only_services_dtos_domain_errors_and_api_wiring(
    controller_module: Path,
) -> None:
    """A controller never reaches a repository, an adapter, an ORM model or domain logic."""
    disallowed_imports = [
        module_name
        for module_name in list_imported_module_names(controller_module)
        if not is_allowed_in_controllers(module_name)
    ]
    assert disallowed_imports == []


@pytest.mark.parametrize(
    ("module_name", "expected_allowed"),
    [
        ("fastapi", True),
        ("emi_copilot.dtos.offer_dtos", True),
        ("emi_copilot.domain.errors", True),
        ("emi_copilot.domain.payments", False),
        ("emi_copilot.repositories.unit_of_work", False),
        ("emi_copilot.adapters.payment_gateway.port", False),
        ("emi_copilot.models.payment_attempt", False),
        ("sqlalchemy", False),
    ],
)
def test_is_allowed_in_controllers_follows_the_layering_table(
    module_name: str, *, expected_allowed: bool
) -> None:
    """The rule itself admits the controller's layers and rejects every other one."""
    assert is_allowed_in_controllers(module_name) is expected_allowed


def test_only_the_composition_root_imports_the_gateway_factory_outside_adapters() -> None:
    """Concrete adapters are chosen in one place, api/dependencies.py (ADR 0008)."""
    importing_modules = [
        describe_source_file(source_file)
        for source_file in list_application_modules()
        if ADAPTERS_DIRECTORY not in source_file.parents
        and GATEWAY_FACTORY_MODULE in list_imported_module_names(source_file)
    ]
    assert importing_modules == [describe_source_file(COMPOSITION_ROOT_FILE)]
