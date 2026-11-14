"""Renders the OpenAPI document exactly as `make openapi` commits it to backend/openapi.json."""

import json
from typing import Any

from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.main import create_application


def build_openapi_document() -> dict[str, Any]:
    """Builds the OpenAPI document of the application; no startup or database is needed."""
    return create_application(ApplicationSettings()).openapi()


def render_openapi_document() -> str:
    """Gives the document as stable, indented JSON with a final newline, ready to commit."""
    return json.dumps(build_openapi_document(), indent=2, ensure_ascii=False) + "\n"
