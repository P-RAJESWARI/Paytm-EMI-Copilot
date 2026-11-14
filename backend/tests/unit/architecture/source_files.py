"""Locations of the application source files that the architecture tests inspect."""

from pathlib import Path

import emi_copilot

APPLICATION_SOURCE_ROOT = Path(emi_copilot.__file__).parent
DOMAIN_DIRECTORY = APPLICATION_SOURCE_ROOT / "domain"
CORE_DIRECTORY = APPLICATION_SOURCE_ROOT / "core"
PAYMENT_GATEWAY_PORT_FILE = APPLICATION_SOURCE_ROOT / "adapters" / "payment_gateway" / "port.py"


def list_domain_modules() -> list[Path]:
    """Lists every Python module under domain/, sorted so test ids are stable."""
    return sorted(DOMAIN_DIRECTORY.rglob("*.py"))


def list_core_modules() -> list[Path]:
    """Lists every Python module under core/, sorted so test ids are stable."""
    return sorted(CORE_DIRECTORY.rglob("*.py"))


def describe_source_file(source_file: Path) -> str:
    """Gives a source file's path relative to the package root, for readable test ids."""
    return str(source_file.relative_to(APPLICATION_SOURCE_ROOT))
