"""Writes backend/openapi.json, the contract the frontend client is generated from."""

from pathlib import Path

from openapi_spec_validator import validate

from emi_copilot.api.openapi_export import build_openapi_document, render_openapi_document

OPENAPI_DOCUMENT_PATH = Path(__file__).resolve().parents[1] / "openapi.json"


def export_openapi_document() -> None:
    """Validates the freshly built document, then writes it where the frontend reads it."""
    validate(build_openapi_document())
    OPENAPI_DOCUMENT_PATH.write_text(render_openapi_document(), encoding="utf-8")


if __name__ == "__main__":
    export_openapi_document()
