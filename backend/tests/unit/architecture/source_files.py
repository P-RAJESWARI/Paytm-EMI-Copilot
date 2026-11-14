"""Locations of the application source files that the architecture tests inspect."""

from pathlib import Path

import emi_copilot

APPLICATION_SOURCE_ROOT = Path(emi_copilot.__file__).parent
DOMAIN_DIRECTORY = APPLICATION_SOURCE_ROOT / "domain"
CORE_DIRECTORY = APPLICATION_SOURCE_ROOT / "core"
CONFIG_DIRECTORY = APPLICATION_SOURCE_ROOT / "config"
SERVICES_DIRECTORY = APPLICATION_SOURCE_ROOT / "services"
CONTROLLERS_DIRECTORY = APPLICATION_SOURCE_ROOT / "api" / "controllers"
ADAPTERS_DIRECTORY = APPLICATION_SOURCE_ROOT / "adapters"
PAYMENT_GATEWAY_PORT_FILE = APPLICATION_SOURCE_ROOT / "adapters" / "payment_gateway" / "port.py"


def list_domain_modules() -> list[Path]:
    """Lists every Python module under domain/, sorted so test ids are stable."""
    return sorted(DOMAIN_DIRECTORY.rglob("*.py"))


def list_core_modules() -> list[Path]:
    """Lists every Python module under core/, sorted so test ids are stable."""
    return sorted(CORE_DIRECTORY.rglob("*.py"))


def list_config_modules() -> list[Path]:
    """Lists every Python module under config/, sorted so test ids are stable."""
    return sorted(CONFIG_DIRECTORY.rglob("*.py"))


def list_services_modules() -> list[Path]:
    """Lists every Python module under services/, sorted so test ids are stable."""
    return sorted(SERVICES_DIRECTORY.rglob("*.py"))


def list_controller_modules() -> list[Path]:
    """Lists every Python module under api/controllers/, sorted so test ids are stable."""
    return sorted(CONTROLLERS_DIRECTORY.rglob("*.py"))


def list_application_modules() -> list[Path]:
    """Lists every Python module of the application, sorted so test ids are stable."""
    return sorted(APPLICATION_SOURCE_ROOT.rglob("*.py"))


def describe_source_file(source_file: Path) -> str:
    """Gives a source file's path relative to the package root, for readable test ids."""
    return str(source_file.relative_to(APPLICATION_SOURCE_ROOT))
